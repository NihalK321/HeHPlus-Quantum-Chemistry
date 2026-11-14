"""SQLite storage for authentic, provenance-preserving peptide records."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .models import SourcePeptideRecord, UpsertResult
from .validation import validate_sequence


def default_database_path() -> Path:
    """Use an ignored local file unless an explicit runtime path is supplied."""

    configured = os.environ.get("PEPPERQ_PEPTIDE_DB")
    if configured:
        return Path(configured).expanduser()
    return Path(__file__).resolve().parent / ".local" / "pepperq_peptides.sqlite3"


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _json_dump(value: Any) -> str:
    return json.dumps(value if value is not None else {}, ensure_ascii=False, sort_keys=True, default=str)


def _json_load(value: str | None, fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def _peptide_id(sequence: str) -> str:
    return f"pep_{hashlib.sha256(sequence.encode('ascii')).hexdigest()[:24]}"


class PeptideRepository:
    """SQLite repository deduplicating exact sequences while retaining sources."""

    def __init__(self, database_path: str | Path | None = None) -> None:
        self.database_path = Path(database_path) if database_path is not None else default_database_path()
        self._connection: sqlite3.Connection | None = None
        self._lock = threading.RLock()

    def initialize(self) -> None:
        """Create the normalized schema if it does not exist."""

        with self._lock:
            connection = self._get_connection()
            connection.executescript(
                """
                PRAGMA foreign_keys = ON;

                CREATE TABLE IF NOT EXISTS peptides (
                    id TEXT PRIMARY KEY,
                    canonical_name TEXT,
                    sequence TEXT NOT NULL UNIQUE,
                    sequence_length INTEGER NOT NULL CHECK (sequence_length > 0),
                    selectable_for_optimization INTEGER NOT NULL CHECK (selectable_for_optimization IN (0, 1)),
                    nonstandard_residues_json TEXT NOT NULL,
                    imported_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS peptide_sources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    peptide_id TEXT NOT NULL REFERENCES peptides(id) ON DELETE CASCADE,
                    source_database TEXT NOT NULL,
                    source_accession TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    source_record_key TEXT NOT NULL,
                    source_name TEXT,
                    parent_protein_accession TEXT,
                    peptide_feature_coordinates_json TEXT,
                    organism TEXT,
                    description TEXT,
                    annotations_json TEXT NOT NULL,
                    modifications_json TEXT NOT NULL,
                    structure_references_json TEXT NOT NULL,
                    available_experimental_properties_json TEXT,
                    evidence_type TEXT,
                    source_version TEXT,
                    retrieval_timestamp TEXT,
                    imported_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE (source_database, source_accession, source_record_key)
                );

                CREATE INDEX IF NOT EXISTS idx_peptides_sequence_length
                    ON peptides(sequence_length);
                CREATE INDEX IF NOT EXISTS idx_peptide_sources_database
                    ON peptide_sources(source_database);
                CREATE INDEX IF NOT EXISTS idx_peptide_sources_peptide_id
                    ON peptide_sources(peptide_id);
                """
            )
            connection.commit()

    def close(self) -> None:
        with self._lock:
            if self._connection is not None:
                self._connection.close()
                self._connection = None

    def upsert(self, record: SourcePeptideRecord) -> UpsertResult:
        """Insert/refresh a provenance record and its exact-sequence peptide."""

        validation = validate_sequence(record.sequence)
        if not validation.is_source_valid:
            raise ValueError(validation.error or "Invalid peptide sequence.")
        if not record.source_database.strip() or not record.source_accession.strip() or not record.source_record_key.strip():
            raise ValueError("Source database, accession, and source record key are required.")
        if not record.source_url.strip():
            raise ValueError("A source URL is required for imported peptide records.")

        sequence = validation.normalized_sequence
        peptide_id = _peptide_id(sequence)
        database = record.source_database.strip()
        accession = record.source_accession.strip()
        record_key = record.source_record_key.strip()
        now = _utc_now()

        with self._lock:
            self.initialize()
            connection = self._get_connection()
            peptide_exists = connection.execute("SELECT 1 FROM peptides WHERE sequence = ?", (sequence,)).fetchone() is not None
            source_exists = connection.execute(
                """
                SELECT 1 FROM peptide_sources
                WHERE source_database = ? AND source_accession = ? AND source_record_key = ?
                """,
                (database, accession, record_key),
            ).fetchone() is not None
            name = record.name.strip() if record.name and record.name.strip() else None

            with connection:
                connection.execute(
                    """
                    INSERT INTO peptides (
                        id, canonical_name, sequence, sequence_length,
                        selectable_for_optimization, nonstandard_residues_json,
                        imported_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(sequence) DO UPDATE SET
                        canonical_name = COALESCE(peptides.canonical_name, excluded.canonical_name),
                        selectable_for_optimization = excluded.selectable_for_optimization,
                        nonstandard_residues_json = excluded.nonstandard_residues_json,
                        updated_at = excluded.updated_at
                    """,
                    (
                        peptide_id,
                        name,
                        sequence,
                        len(sequence),
                        int(validation.selectable_for_optimization),
                        _json_dump(list(validation.nonstandard_residues)),
                        now,
                        now,
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO peptide_sources (
                        peptide_id, source_database, source_accession, source_url,
                        source_record_key, source_name, parent_protein_accession,
                        peptide_feature_coordinates_json, organism, description,
                        annotations_json, modifications_json, structure_references_json,
                        available_experimental_properties_json, evidence_type,
                        source_version, retrieval_timestamp, imported_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(source_database, source_accession, source_record_key) DO UPDATE SET
                        peptide_id = excluded.peptide_id,
                        source_url = excluded.source_url,
                        source_name = excluded.source_name,
                        parent_protein_accession = excluded.parent_protein_accession,
                        peptide_feature_coordinates_json = excluded.peptide_feature_coordinates_json,
                        organism = excluded.organism,
                        description = excluded.description,
                        annotations_json = excluded.annotations_json,
                        modifications_json = excluded.modifications_json,
                        structure_references_json = excluded.structure_references_json,
                        available_experimental_properties_json = excluded.available_experimental_properties_json,
                        evidence_type = excluded.evidence_type,
                        source_version = excluded.source_version,
                        retrieval_timestamp = excluded.retrieval_timestamp,
                        updated_at = excluded.updated_at
                    """,
                    (
                        peptide_id,
                        database,
                        accession,
                        record.source_url.strip(),
                        record_key,
                        name,
                        record.parent_protein_accession,
                        _json_dump(record.peptide_feature_coordinates) if record.peptide_feature_coordinates is not None else None,
                        record.organism,
                        record.description,
                        _json_dump(record.annotations),
                        _json_dump(record.modifications),
                        _json_dump(record.structure_references),
                        _json_dump(record.available_experimental_properties)
                        if record.available_experimental_properties is not None
                        else None,
                        record.evidence_type,
                        record.source_version,
                        record.retrieval_timestamp,
                        now,
                        now,
                    ),
                )
            return UpsertResult(
                peptide_id=peptide_id,
                peptide_created=not peptide_exists,
                source_reference_created=not source_exists,
                selectable_for_optimization=validation.selectable_for_optimization,
            )

    def search(
        self,
        *,
        search: str | None = None,
        source: str | None = None,
        minimum_length: int | None = None,
        maximum_length: int | None = None,
        annotation: str | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> dict[str, Any]:
        """Perform bounded, parameterized search and pagination."""

        self._validate_page_arguments(page, page_size, minimum_length, maximum_length)
        with self._lock:
            self.initialize()
            conditions, parameters = self._search_conditions(
                search=search,
                source=source,
                minimum_length=minimum_length,
                maximum_length=maximum_length,
                annotation=annotation,
            )
            where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
            connection = self._get_connection()
            total = int(connection.execute(f"SELECT COUNT(*) FROM peptides p{where}", parameters).fetchone()[0])
            rows = connection.execute(
                f"""
                SELECT p.* FROM peptides p{where}
                ORDER BY p.updated_at DESC, p.id ASC
                LIMIT ? OFFSET ?
                """,
                [*parameters, page_size, (page - 1) * page_size],
            ).fetchall()
            return {
                "items": [self._serialize_peptide(row, include_sources=True) for row in rows],
                "page": page,
                "pageSize": page_size,
                "total": total,
                "totalPages": (total + page_size - 1) // page_size if total else 0,
            }

    def get(self, peptide_id: str) -> dict[str, Any] | None:
        with self._lock:
            self.initialize()
            row = self._get_connection().execute("SELECT * FROM peptides WHERE id = ?", (peptide_id,)).fetchone()
            return self._serialize_peptide(row, include_sources=True) if row is not None else None

    def stats(self) -> dict[str, Any]:
        """Report database counts without turning absent data into a claim."""

        with self._lock:
            self.initialize()
            connection = self._get_connection()
            by_source = connection.execute(
                """
                SELECT source_database, COUNT(*) AS record_count
                FROM peptide_sources
                GROUP BY source_database
                ORDER BY source_database COLLATE NOCASE ASC
                """
            ).fetchall()
            return {
                "totalImportedRecords": int(connection.execute("SELECT COUNT(*) FROM peptides").fetchone()[0]),
                "totalSourceRecords": int(connection.execute("SELECT COUNT(*) FROM peptide_sources").fetchone()[0]),
                "bySource": [
                    {"sourceDatabase": row["source_database"], "recordCount": int(row["record_count"])}
                    for row in by_source
                ],
                "withStructures": self._count_distinct_source_field("structure_references_json"),
                "withExperimentalAnnotations": self._count_distinct_source_field(
                    "available_experimental_properties_json"
                ),
            }

    def _get_connection(self) -> sqlite3.Connection:
        if self._connection is None:
            self.database_path.parent.mkdir(parents=True, exist_ok=True)
            self._connection = sqlite3.connect(self.database_path, check_same_thread=False)
            self._connection.row_factory = sqlite3.Row
            self._connection.execute("PRAGMA foreign_keys = ON")
            self._connection.execute("PRAGMA journal_mode = WAL")
        return self._connection

    @staticmethod
    def _validate_page_arguments(
        page: int,
        page_size: int,
        minimum_length: int | None,
        maximum_length: int | None,
    ) -> None:
        if page < 1:
            raise ValueError("page must be at least 1.")
        if page_size < 1 or page_size > 100:
            raise ValueError("page_size must be between 1 and 100.")
        if minimum_length is not None and minimum_length < 0:
            raise ValueError("minimum_length cannot be negative.")
        if maximum_length is not None and maximum_length < 0:
            raise ValueError("maximum_length cannot be negative.")
        if minimum_length is not None and maximum_length is not None and minimum_length > maximum_length:
            raise ValueError("minimum_length cannot exceed maximum_length.")

    @staticmethod
    def _search_conditions(
        *,
        search: str | None,
        source: str | None,
        minimum_length: int | None,
        maximum_length: int | None,
        annotation: str | None,
    ) -> tuple[list[str], list[Any]]:
        conditions: list[str] = []
        parameters: list[Any] = []
        if search and search.strip():
            pattern = f"%{search.strip().lower()}%"
            conditions.append(
                """(
                    LOWER(p.sequence) LIKE ? OR LOWER(COALESCE(p.canonical_name, '')) LIKE ?
                    OR EXISTS (
                        SELECT 1 FROM peptide_sources ps WHERE ps.peptide_id = p.id
                        AND (LOWER(COALESCE(ps.source_name, '')) LIKE ?
                             OR LOWER(COALESCE(ps.description, '')) LIKE ?)
                    )
                )"""
            )
            parameters.extend([pattern, pattern, pattern, pattern])
        if source and source.strip():
            conditions.append(
                """EXISTS (
                    SELECT 1 FROM peptide_sources ps
                    WHERE ps.peptide_id = p.id AND LOWER(ps.source_database) = ?
                )"""
            )
            parameters.append(source.strip().lower())
        if minimum_length is not None:
            conditions.append("p.sequence_length >= ?")
            parameters.append(minimum_length)
        if maximum_length is not None:
            conditions.append("p.sequence_length <= ?")
            parameters.append(maximum_length)
        if annotation and annotation.strip():
            conditions.append(
                """EXISTS (
                    SELECT 1 FROM peptide_sources ps
                    WHERE ps.peptide_id = p.id AND LOWER(ps.annotations_json) LIKE ?
                )"""
            )
            parameters.append(f"%{annotation.strip().lower()}%")
        return conditions, parameters

    def _count_distinct_source_field(self, field: str) -> int:
        if field not in {"structure_references_json", "available_experimental_properties_json"}:
            raise ValueError("Unsupported source metadata field.")
        return int(
            self._get_connection()
            .execute(
                f"""
                SELECT COUNT(DISTINCT peptide_id) FROM peptide_sources
                WHERE {field} IS NOT NULL AND {field} NOT IN ('[]', '{{}}', 'null')
                """
            )
            .fetchone()[0]
        )

    def _serialize_peptide(self, row: sqlite3.Row, *, include_sources: bool) -> dict[str, Any]:
        sources = [
            self._serialize_source(source_row)
            for source_row in self._get_connection()
            .execute(
                """
                SELECT * FROM peptide_sources WHERE peptide_id = ?
                ORDER BY source_database COLLATE NOCASE ASC, source_accession ASC, id ASC
                """,
                (row["id"],),
            )
            .fetchall()
        ]
        primary_source = sources[0] if sources else None
        result: dict[str, Any] = {
            "id": row["id"],
            "name": row["canonical_name"] or (primary_source or {}).get("name") or "Unnamed peptide",
            "sequence": row["sequence"],
            "sequenceLength": int(row["sequence_length"]),
            "selectableForOptimization": bool(row["selectable_for_optimization"]),
            "nonstandardResidues": _display_nonstandard_residues(
                _json_load(row["nonstandard_residues_json"], [])
            ),
            "importedAt": row["imported_at"],
            "updatedAt": row["updated_at"],
            "sourceCount": len(sources),
            "primarySource": primary_source,
        }
        if include_sources:
            result["sourceReferences"] = sources
        return result

    @staticmethod
    def _serialize_source(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": str(row["id"]),
            "sourceDatabase": row["source_database"],
            "sourceAccession": row["source_accession"],
            "sourceUrl": row["source_url"],
            "sourceRecordKey": row["source_record_key"],
            "name": row["source_name"],
            "parentProteinAccession": row["parent_protein_accession"],
            "peptideFeatureCoordinates": _serialize_feature_coordinates(
                _json_load(row["peptide_feature_coordinates_json"], None)
            ),
            "organism": row["organism"],
            "description": row["description"],
            "annotations": _json_load(row["annotations_json"], []),
            "modifications": _json_load(row["modifications_json"], []),
            "structureReferences": _json_load(row["structure_references_json"], []),
            "availableExperimentalProperties": _json_load(row["available_experimental_properties_json"], None),
            "evidenceType": row["evidence_type"],
            "sourceVersion": row["source_version"],
            "retrievalTimestamp": row["retrieval_timestamp"],
            "importedAt": row["imported_at"],
            "updatedAt": row["updated_at"],
        }


def _display_nonstandard_residues(value: Any) -> list[str]:
    """Expose source flags as readable strings for the selection interface."""

    if not isinstance(value, list):
        return []
    labels: list[str] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        residue = item.get("residue")
        position = item.get("position")
        if isinstance(residue, str) and isinstance(position, int):
            labels.append(f"{residue} at position {position}")
    return labels


def _serialize_feature_coordinates(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    start = value.get("start")
    end = value.get("end")
    if not isinstance(start, int) or not isinstance(end, int):
        return None
    result: dict[str, Any] = {
        "start": start,
        "end": end,
        "coordinateSystem": value.get("coordinateSystem") or value.get("coordinate_system") or "Source coordinates",
    }
    feature_id = value.get("featureId") or value.get("feature_id")
    if isinstance(feature_id, str):
        result["featureId"] = feature_id
    return result
