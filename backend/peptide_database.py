"""Local sequence index of DBAASP records plus the project's small references.

Download/update with ``python -m backend.peptide_database sync``. Source data
is attributed to DBAASP (https://dbaasp.org), doi:10.1093/nar/gkaa991.
Only standard, uppercase, single-chain sequences are indexed. Sequence matches
do not verify chemical modifications or establish biological activity.
"""

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
import ssl

import httpx

from class_computing_.classic_computing_solution import PeptideTable
from .schema import PeptideLookupRequest, STANDARD_AMINO_ACIDS


DBAASP_URL = "https://dbaasp.org"
ATTRIBUTION = "Peptide data from DBAASP (https://dbaasp.org); https://doi.org/10.1093/nar/gkaa991"


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def http_client():
    # System trust includes the Windows certificate store. Never disable TLS.
    return httpx.Client(verify=ssl.create_default_context(), timeout=20, follow_redirects=True)


class PeptideDatabase:
    def __init__(self, path=None):
        self.path = Path(path or os.getenv("PEPTIDE_DATABASE_PATH") or Path(__file__).parent / ".peptide_cache" / "catalog.sqlite3")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS peptides (
                    id TEXT PRIMARY KEY, source TEXT NOT NULL, name TEXT NOT NULL,
                    sequence TEXT NOT NULL, length INTEGER NOT NULL,
                    source_url TEXT NOT NULL, info TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS peptide_sequence ON peptides(sequence);
                CREATE INDEX IF NOT EXISTS peptide_length ON peptides(length);
                CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS details (id TEXT PRIMARY KEY, fetched_at TEXT NOT NULL, info TEXT NOT NULL);
            """)
            # Preserve the original curated examples alongside the larger source.
            for sequence, record in PeptideTable().peptides.items():
                self._insert(db, f"local:{record['name']}", "local_reference", record["name"], sequence,
                             record["source_url"], record)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def _insert(db, identifier, source, name, sequence, url, info):
        db.execute("INSERT OR REPLACE INTO peptides VALUES (?, ?, ?, ?, ?, ?, ?)",
                   (identifier, source, name, sequence, len(sequence), url, json.dumps(info)))

    def status(self):
        with self.connect() as db:
            counts = {row["source"]: row["n"] for row in db.execute("SELECT source, count(*) n FROM peptides GROUP BY source")}
            metadata = {row["key"]: json.loads(row["value"]) for row in db.execute("SELECT * FROM metadata")}
        return {"indexed_records": sum(counts.values()), "sources": counts, "sync": metadata,
                "attribution": ATTRIBUTION,
                "scope": "DBAASP antimicrobial/cytotoxic peptides plus local references; not all known peptides."}

    def sync(self, client=None, progress=print):
        """Fetch paginated summaries, then replace the source index atomically.

        Failed downloads leave the previously imported catalog intact. No
        individual-detail harvesting is performed during bulk synchronization.
        """
        if client is None:
            with http_client() as owned:
                return self.sync(owned, progress)
        records = {}
        offset = 0
        total = None
        skipped = 0
        while total is None or offset < total:
            response = client.get(f"{DBAASP_URL}/peptides", params={"limit": 1000, "offset": offset})
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict) or not isinstance(payload.get("data"), list) or not isinstance(payload.get("totalCount"), int):
                raise ValueError("DBAASP returned an unexpected search response.")
            if total is None:
                total = payload["totalCount"]
                if not 0 <= total <= 200000:
                    raise ValueError("Unexpected source size; existing catalog was preserved.")
            if not payload["data"] and offset < total:
                raise ValueError("DBAASP pagination ended early; existing catalog was preserved.")
            for record in payload["data"]:
                sequence = record.get("sequence") or ""
                complexity = record.get("complexity") or ""
                # Lowercase can encode D-residues: do not uppercase source data.
                if (complexity.lower() != "monomer" or not 2 <= len(sequence) <= 200
                        or any(code not in STANDARD_AMINO_ACIDS for code in sequence)):
                    skipped += 1
                    continue
                identifier = record.get("id")
                if not isinstance(identifier, int):
                    raise ValueError("DBAASP record has no valid identifier.")
                records[f"dbaasp:{identifier}"] = record
            offset += len(payload["data"])
            if progress:
                progress(f"Downloaded {offset}/{total} source records; {len(records)} standard single-chain records retained.", flush=True)

        with self.connect() as db:
            db.execute("DELETE FROM peptides WHERE source = 'DBAASP'")
            for identifier, record in records.items():
                info = {"n_terminus": record.get("nTerminus") or record.get("NTerminus"),
                        "c_terminus": record.get("cTerminus") or record.get("CTerminus")}
                self._insert(db, identifier, "DBAASP", record.get("name") or record.get("dbaaspId") or identifier,
                             record["sequence"], f"https://dbaasp.org/peptide-card?id={record['id']}", info)
            metadata = {"last_sync_utc": utc_now(), "source_total": total, "downloaded": offset,
                        "indexed_from_source": len(records), "skipped": skipped}
            for key, value in metadata.items():
                db.execute("INSERT OR REPLACE INTO metadata VALUES (?, ?)", (key, json.dumps(value)))
            db.execute("DELETE FROM details")
        return self.status()

    def _details(self, identifier, client=None):
        with self.connect() as db:
            cached = db.execute("SELECT info, fetched_at FROM details WHERE id = ?", (identifier,)).fetchone()
        if cached:
            return {**json.loads(cached["info"]), "details_fetched_at": cached["fetched_at"]}
        if client is None:
            with http_client() as owned:
                return self._details(identifier, owned)
        response = client.get(f"{DBAASP_URL}/peptides/{identifier.split(':')[1]}")
        response.raise_for_status()
        raw = response.json()
        if not isinstance(raw, dict) or str(raw.get("id")) != identifier.split(":")[1]:
            raise ValueError("DBAASP returned an unexpected detail response.")
        activities = []
        for key, category in (("targetActivities", "antimicrobial"),
                              ("hemoliticCytotoxicActivities", "hemolytic_or_cytotoxic"),
                              ("antibiofilmActivities", "antibiofilm")):
            for activity in (raw.get(key) or [])[:20]:
                def name(value):
                    return value.get("name") if isinstance(value, dict) else value
                activities.append({"category": category,
                    "target": name(activity.get("targetSpecies")),
                    "measure": activity.get("activityMeasureValue") or name(activity.get("activityMeasureGroup")),
                    "reported_concentration": activity.get("concentration"),
                    "unit": name(activity.get("unit")), "medium": name(activity.get("medium")),
                    "ph": activity.get("ph"), "notes": activity.get("note"),
                    "reference": activity.get("reference")})
        references = [{"title": item.get("title"), "year": item.get("year"),
                       "pubmed_id": (item.get("pubmed") or {}).get("pubmedId")}
                      for item in (raw.get("articles") or [])]
        info = {"reference_sequence": raw.get("sequence"), "activities": activities,
                "activity_rows_truncated": any(len(raw.get(key) or []) > 20 for key in
                    ("targetActivities", "hemoliticCytotoxicActivities", "antibiofilmActivities")),
                "references": references,
                "structural_annotations": {key: raw.get(key) for key in
                    ("nTerminus", "cTerminus", "unusualAminoAcids", "intrachainBonds", "interchainBonds")}}
        fetched_at = utc_now()
        with self.connect() as db:
            db.execute("INSERT OR REPLACE INTO details VALUES (?, ?, ?)", (identifier, fetched_at, json.dumps(info)))
        return {**info, "details_fetched_at": fetched_at}

    def lookup(self, request: PeptideLookupRequest, client=None):
        with self.connect() as db:
            total = db.execute("SELECT count(*) FROM peptides WHERE sequence = ?", (request.sequence,)).fetchone()[0]
            exact = db.execute("SELECT * FROM peptides WHERE sequence = ? ORDER BY source, id LIMIT ?",
                               (request.sequence, request.limit)).fetchall()
            others = db.execute("SELECT * FROM peptides WHERE length = ? AND sequence != ?",
                                (len(request.sequence), request.sequence)).fetchall() if request.include_similar else []
        matches = []
        for row in exact:
            match = self._match(row, "exact_backbone_sequence", 1.0)
            if request.include_details and row["source"] == "DBAASP":
                try:
                    details = self._details(row["id"], client)
                    if details["reference_sequence"] != request.sequence:
                        match["detail_status"] = "Source sequence changed; refresh the local catalog."
                    else:
                        match.update(details)
                        match["detail_status"] = "available"
                except (httpx.HTTPError, ValueError, TypeError, KeyError):
                    match["detail_status"] = "Source details unavailable; sequence match is from the local index."
            matches.append(match)
        ranked = []
        for row in others:
            identity = sum(a == b for a, b in zip(request.sequence, row["sequence"])) / len(request.sequence)
            if identity >= request.minimum_identity:
                ranked.append((identity, row))
        ranked.sort(key=lambda item: (-item[0], item[1]["id"]))
        similar = [self._match(row, "same_length_positional_similarity", identity)
                   for identity, row in ranked[:request.limit]]
        return {"query_sequence": request.sequence, "exact_match_count": total,
                "exact_matches": matches, "similar_sequences": similar, "database": self.status(),
                "interpretation": [
                    "Matches compare complete backbone sequences; chemical identity and effects are not verified.",
                    "Similarities are ungapped, same-length positional identities, not activity predictions or probabilities.",
                    "Assay measurements describe reference peptides under reported experimental conditions.",
                    "No match means not found in this local catalog, not biologically inactive.",
                ]}

    @staticmethod
    def _match(row, kind, identity):
        info = json.loads(row["info"])
        return {"id": row["id"], "name": row["name"], "sequence": row["sequence"],
                "match_type": kind, "sequence_identity": identity, "source": row["source"],
                "source_url": row["source_url"],
                "documented_role": info.get("effect") if kind == "exact_backbone_sequence" else None,
                "structure_notes": info.get("structure_notes"),
                "n_terminus": info.get("n_terminus"), "c_terminus": info.get("c_terminus"),
                "detail_status": "local_reference" if row["source"] == "local_reference" else "not_requested"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["sync", "status"])
    arguments = parser.parse_args()
    database = PeptideDatabase()
    try:
        result = database.sync() if arguments.command == "sync" else database.status()
    except (httpx.HTTPError, ValueError) as error:
        parser.exit(1, f"Catalog sync failed; the existing catalog was preserved. {error}\n")
    print(json.dumps(result, indent=2))
