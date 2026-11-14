"""Read the existing local libraries without modifying their schemas or data."""

from functools import lru_cache
import json
import os
from pathlib import Path
import sqlite3

from ..peptide_library.storage import default_database_path
from ..schema import STANDARD_AMINO_ACIDS


def _file_signature(path):
    return (path.stat().st_mtime_ns, path.stat().st_size) if path.exists() else (0, 0)


def _connect(path):
    connection = sqlite3.connect(str(path))
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only=ON")
    return connection


def _standard(sequence):
    return 2 <= len(sequence) <= 200 and all(letter in STANDARD_AMINO_ACIDS for letter in sequence)


@lru_cache(maxsize=2)
def _snapshot(library_path, legacy_path, signature):
    records = []
    seen_sequences = set()
    imported = 0
    excluded = 0
    if Path(library_path).exists():
        connection = _connect(library_path)
        try:
            peptides = connection.execute("SELECT * FROM peptides ORDER BY id").fetchall()
            sources = {}
            for source in connection.execute("SELECT * FROM peptide_sources ORDER BY id"):
                sources.setdefault(source["peptide_id"], []).append(source)
            imported += len(peptides)
            for peptide in peptides:
                sequence = peptide["sequence"]
                # Do not replace a known modified source with a less detailed
                # legacy occurrence of the same sequence.
                seen_sequences.add(sequence)
                eligible_sources = [s for s in sources.get(peptide["id"], [])
                                    if not json.loads(s["modifications_json"] or "[]")]
                if not peptide["selectable_for_optimization"] or not _standard(sequence) or not eligible_sources:
                    excluded += 1
                    continue
                source = eligible_sources[0]
                records.append({"id": f"library:{peptide['id']}", "name": peptide["canonical_name"] or source["source_name"] or "Unnamed peptide",
                    "sequence": sequence, "source": source["source_database"],
                    "accession": source["source_accession"], "source_url": source["source_url"],
                    "retrieved_at": source["retrieval_timestamp"], "source_version": source["source_version"]})
        finally:
            connection.close()

    if Path(legacy_path).exists():
        connection = _connect(legacy_path)
        try:
            for row in connection.execute("SELECT * FROM peptides ORDER BY id"):
                imported += 1
                sequence = row["sequence"]
                if sequence in seen_sequences:
                    continue
                info = json.loads(row["info"])
                notes = info.get("structure_notes", "").lower()
                has_modification = bool(info.get("n_terminus") or info.get("c_terminus"))
                has_modification |= any(word in notes for word in ("disulfide", "amidated", "fatty", "hexenoyl"))
                has_modification |= any(word in row["name"].lower() for word in ("cyclo(", "cyclic", "disulfide"))
                if not _standard(sequence) or has_modification:
                    excluded += 1
                    continue
                seen_sequences.add(sequence)
                records.append({"id": row["id"], "name": row["name"], "sequence": sequence,
                    "source": row["source"], "accession": row["id"], "source_url": row["source_url"],
                    "retrieved_at": None, "source_version": None})
        finally:
            connection.close()
    return records, {"imported_source_records": imported, "unique_eligible_sequences": len(records),
                     "excluded_modified_or_unsupported_records": excluded,
                     "sources": sorted({record["source"] for record in records})}


class BlendCatalog:
    def __init__(self, library_path=None, legacy_path=None):
        self.library_path = Path(library_path or default_database_path()).resolve()
        default_legacy = Path(__file__).resolve().parents[1] / ".peptide_cache" / "catalog.sqlite3"
        self.legacy_path = Path(legacy_path or os.getenv("PEPTIDE_DATABASE_PATH") or default_legacy).resolve()

    def load(self):
        signature = (_file_signature(self.library_path), _file_signature(Path(str(self.library_path) + "-wal")),
                     _file_signature(self.legacy_path), _file_signature(Path(str(self.legacy_path) + "-wal")))
        return _snapshot(str(self.library_path), str(self.legacy_path), signature)

    def search(self, search="", page=1, page_size=20):
        records, stats = self.load()
        query = search.strip().casefold()
        matches = [row for row in records if not query or query in f"{row['name']} {row['sequence']} {row['accession']}".casefold()]
        start = (page - 1) * page_size
        return {"items": matches[start:start + page_size], "total": len(matches), "page": page,
                "page_size": page_size, "catalog": stats}
