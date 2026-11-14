"""Standalone, additive PepperQ peptide/modified-peptide catalog.

Never writes to PepperQ's existing database. Standard library only.
Run from the repo root: python backend/peptide_library/extra_catalog.py --help
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sqlite3
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = ROOT / "data" / "pepperq_extras.sqlite"
CANONICAL_AA = set("ACDEFGHIKLMNPQRSTVWY")
USER_AGENT = "PepperQ/0.1 (research prototype; courteous public API client)"


def fetch_json(url: str, *, retries: int = 3) -> tuple[dict, dict]:
    """Read a JSON object and response headers with bounded retries."""
    for attempt in range(retries):
        try:
            req = Request(url, headers={"Accept": "application/json", "User-Agent": USER_AGENT})
            with urlopen(req, timeout=25) as response:
                data = json.load(response)
                if not isinstance(data, dict):
                    raise ValueError("Unexpected non-object API response")
                return data, dict(response.headers.items())
        except HTTPError as exc:
            if exc.code not in {429, 500, 502, 503, 504} or attempt == retries - 1:
                raise
            retry_after = exc.headers.get("Retry-After", "")
            delay = min(float(retry_after), 20.0) if retry_after.replace(".", "", 1).isdigit() else 2 ** (attempt + 1)
            time.sleep(delay)
        except (URLError, TimeoutError):
            if attempt == retries - 1:
                raise
            time.sleep(2 ** (attempt + 1))
    raise RuntimeError("API failed")


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute("""CREATE TABLE IF NOT EXISTS extra_peptides (
      id TEXT PRIMARY KEY,
      kind TEXT NOT NULL,
      display_name TEXT NOT NULL,
      sequence TEXT,
      search_text TEXT NOT NULL,
      record_json TEXT NOT NULL,
      imported_at TEXT NOT NULL
    )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_extra_kind ON extra_peptides(kind)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_extra_name ON extra_peptides(display_name)")
    conn.commit()


def open_db(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    init_db(conn)
    return conn


def save_record(conn: sqlite3.Connection, record: dict) -> None:
    if not record.get("id") or not record.get("name") or not record.get("source_references"):
        raise ValueError("Record must include an ID, name and source reference")
    aliases = record.get("synonyms", [])
    search_text = " ".join([record["id"], record["name"], record.get("sequence") or ""] + aliases).casefold()
    conn.execute("""INSERT INTO extra_peptides(id,kind,display_name,sequence,search_text,record_json,imported_at)
      VALUES (?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET
      kind=excluded.kind,display_name=excluded.display_name,sequence=excluded.sequence,
      search_text=excluded.search_text,record_json=excluded.record_json,imported_at=excluded.imported_at""",
      (record["id"], record["kind"], record["name"], record.get("sequence"), search_text,
       json.dumps(record, sort_keys=True), dt.datetime.now(dt.timezone.utc).isoformat()))
    conn.commit()


def parse_uniprot_entry(entry: dict) -> list[dict]:
    """Extract annotated mature PEPTIDE features, not precursor proteins."""
    accession = entry.get("primaryAccession")
    parent = (entry.get("sequence") or {}).get("value")
    if not accession or not isinstance(parent, str):
        return []
    out: list[dict] = []
    for feature in entry.get("features") or []:
        if feature.get("type", "").casefold() != "peptide":
            continue
        loc = feature.get("location") or {}
        start = (loc.get("start") or {}).get("value")
        end = (loc.get("end") or {}).get("value")
        if not isinstance(start, int) or not isinstance(end, int) or start < 1 or end > len(parent) or end < start:
            continue
        seq = parent[start - 1:end].upper()
        if not seq or len(seq) > 300 or not set(seq) <= CANONICAL_AA:
            continue
        feature_id = feature.get("featureId")
        suffix = feature_id if isinstance(feature_id, str) and feature_id else f"{start}-{end}"
        label = feature.get("description") or f"Peptide {start}-{end} from {accession}"
        out.append({
            "id": f"uniprot:{accession}:{suffix}",
            "kind": "annotated_mature_peptide", "name": label,
            "sequence": seq, "sequence_length": len(seq),
            "parent_accession": accession, "coordinates": {"start": start, "end": end},
            "synonyms": [accession, suffix],
            "qaoa_sequence_supported": True,
            "sequence_only_scoring_caveat": "Check biological modifications and termini before quantitative chemistry scoring",
            "source_references": [{"database": "UniProtKB", "accession": accession,
                                   "url": f"https://www.uniprot.org/uniprotkb/{accession}/entry"}],
            "evidence": feature.get("evidences", []),
            "provenance": "Annotated UniProtKB PEPTIDE feature; sequence is extracted from parent",
        })
    return out


def parse_next_link(headers: dict) -> str | None:
    link = headers.get("Link") or headers.get("link") or ""
    for segment in link.split(","):
        match = re.search(r'<([^>]+)>\s*;\s*rel="?next"?', segment)
        if match:
            url = match.group(1)
            if url.startswith("https://rest.uniprot.org/"):
                return url
    return None


def import_uniprot(conn: sqlite3.Connection, limit: int, reviewed_only: bool = False) -> dict:
    if not 1 <= limit <= 100000:
        raise ValueError("--limit must be between 1 and 100000")
    query = "ft_peptide:*" + (" AND reviewed:true" if reviewed_only else "")
    url = "https://rest.uniprot.org/uniprotkb/search?" + urlencode({"query": query, "format": "json", "size": 100})
    added = 0
    pages = 0
    seen = set()
    while url and added < limit:
        if url in seen:
            raise RuntimeError("Repeated UniProt pagination link")
        seen.add(url)
        data, headers = fetch_json(url)
        pages += 1
        results = data.get("results") or []
        if not isinstance(results, list):
            raise ValueError("Unexpected UniProt results schema")
        for entry in results:
            for record in parse_uniprot_entry(entry):
                save_record(conn, record)
                added += 1
                if added >= limit:
                    break
            if added >= limit:
                break
        print(f"UniProt: processed page {pages}; upserted {added} annotated peptides", flush=True)
        url = parse_next_link(headers)
        if not results:
            break
        time.sleep(0.25)
    return {"upserted": added, "pages": pages}


def parse_retatrutide(pubchem: dict | None, chembl: dict | None) -> dict:
    if pubchem is None and chembl is None:
        raise ValueError("At least one verified source response is required")
    props = {}
    synonyms = ["retatrutide", "LY3437943", "LY-3437943"]
    references = []
    if pubchem is not None:
        rows = (pubchem.get("PropertyTable") or {}).get("Properties") or []
        if len(rows) != 1 or rows[0].get("CID") != 171390338:
            raise ValueError("PubChem response did not confirm CID 171390338")
        props = rows[0]
        references.append({"database": "PubChem", "accession": "171390338",
                           "url": "https://pubchem.ncbi.nlm.nih.gov/compound/171390338"})
    if chembl is not None:
        if chembl.get("molecule_chembl_id") != "CHEMBL5095485":
            raise ValueError("ChEMBL response did not confirm CHEMBL5095485")
        references.append({"database": "ChEMBL", "accession": "CHEMBL5095485",
                           "url": "https://www.ebi.ac.uk/chembl/explore/compound/CHEMBL5095485"})
        for s in chembl.get("molecule_synonyms") or []:
            name = s.get("molecule_synonym") if isinstance(s, dict) else None
            if isinstance(name, str) and len(name) <= 100:
                synonyms.append(name)
    return {
        "id": "pubchem:171390338", "name": "Retatrutide", "kind": "modified_peptide",
        "synonyms": sorted(set(synonyms), key=str.casefold),
        "sequence": None,  # Do not invent a sequence from a chemical structure
        "qaoa_sequence_supported": False,
        "exclusion_reason": "Lipidated/modified peptide: simplified sequence chemistry is incomplete",
        "structure": {
            "smiles": props.get("SMILES") or props.get("ConnectivitySMILES"),
            "inchi_key": props.get("InChIKey"),
            "formula": props.get("MolecularFormula"),
            "molecular_weight_g_mol": props.get("MolecularWeight"),
            "chembl_canonical_smiles": ((chembl or {}).get("molecule_structures") or {}).get("canonical_smiles"),
        },
        "source_references": references,
        "status": "investigational_research_compound",
        "provenance": "PubChem/ChEMBL public compound identifiers; data fetched from live APIs",
    }


def import_retatrutide(conn: sqlite3.Connection) -> dict:
    pubchem = None
    chembl = None
    errors = []
    for name, url in [
        ("PubChem", "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/171390338/property/MolecularFormula,MolecularWeight,SMILES,InChIKey/JSON"),
        ("ChEMBL", "https://www.ebi.ac.uk/chembl/api/data/molecule/CHEMBL5095485.json"),
    ]:
        try:
            payload, _ = fetch_json(url)
            if name == "PubChem":
                pubchem = payload
            else:
                chembl = payload
        except Exception as exc:
            errors.append(f"{name}: {exc}")
    if pubchem is None and chembl is None:
        raise RuntimeError("No source accessible: " + "; ".join(errors))
    record = parse_retatrutide(pubchem, chembl)
    save_record(conn, record)
    return {"record": record, "warnings": errors}


def search_records(conn: sqlite3.Connection, query: str, limit: int = 25, offset: int = 0) -> dict:
    if limit < 1 or limit > 100 or offset < 0:
        raise ValueError("Invalid pagination")
    escaped = query.casefold().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    where = "WHERE search_text LIKE ? ESCAPE '\\'" if query else ""
    params = (f"%{escaped}%",) if query else ()
    total = conn.execute(f"SELECT count(*) FROM extra_peptides {where}", params).fetchone()[0]
    rows = conn.execute(f"SELECT record_json FROM extra_peptides {where} ORDER BY display_name LIMIT ? OFFSET ?",
                        params + (limit, offset)).fetchall()
    return {"total": total, "results": [json.loads(row[0]) for row in rows]}


def get_record(conn: sqlite3.Connection, record_id: str) -> dict | None:
    row = conn.execute("SELECT record_json FROM extra_peptides WHERE id=?", (record_id,)).fetchone()
    return json.loads(row[0]) if row else None


def get_stats(conn: sqlite3.Connection) -> dict:
    counts = conn.execute("SELECT kind, count(*) FROM extra_peptides GROUP BY kind ORDER BY kind").fetchall()
    return {"total": sum(n for _, n in counts), "by_kind": dict(counts), "store": "separate additive catalog"}


def export_jsonl(conn: sqlite3.Connection, dest: Path) -> int:
    dest.parent.mkdir(parents=True, exist_ok=True)
    rows = conn.execute("SELECT record_json FROM extra_peptides ORDER BY id").fetchall()
    with dest.open("w", encoding="utf-8") as handle:
        for (line,) in rows:
            handle.write(line + "\n")
    return len(rows)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", type=Path, default=DEFAULT_DB, help="Separate SQLite catalog path")
    sub = ap.add_subparsers(dest="command", required=True)
    sub.add_parser("import-retatrutide", help="Fetch verified PubChem/ChEMBL record")
    u = sub.add_parser("import-uniprot", help="Import additional annotated mature peptides")
    u.add_argument("--limit", type=int, default=1000)
    u.add_argument("--reviewed-only", action="store_true")
    s = sub.add_parser("search", help="Search the additive catalog")
    s.add_argument("query", nargs="?", default="")
    s.add_argument("--limit", type=int, default=25)
    s.add_argument("--offset", type=int, default=0)
    sub.add_parser("stats")
    e = sub.add_parser("export-jsonl")
    e.add_argument("output", type=Path)
    args = ap.parse_args()
    with open_db(args.db) as conn:
        if args.command == "import-retatrutide":
            result = import_retatrutide(conn)
        elif args.command == "import-uniprot":
            result = import_uniprot(conn, args.limit, args.reviewed_only)
        elif args.command == "search":
            result = search_records(conn, args.query, args.limit, args.offset)
        elif args.command == "stats":
            result = get_stats(conn)
        else:
            result = {"exported": export_jsonl(conn, args.output), "output": str(args.output)}
        print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
