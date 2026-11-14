"""Connector for the documented DBAASP public peptide API.

DBAASP records can describe monomers, multimers, and multi-peptide complexes.
Only an explicit sequence-bearing monomer is imported as a selectable peptide;
the connector never concatenates complex chains.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import Any
from urllib.parse import urlencode
import re

from .http_client import JsonHttpClient, JsonResponse, SourceRequestError
from .models import SourcePeptideRecord


DBAASP_PEPTIDES_URL = "https://dbaasp.org/peptides"
MAX_DBAASP_PAGE_SIZE = 100


class DbaaspPeptideConnector:
    """Fetch explicit DBAASP peptide records with their source provenance."""

    source_name = "DBAASP"

    def __init__(self, http_client: JsonHttpClient | None = None) -> None:
        self.http_client = http_client or JsonHttpClient()

    def iter_peptides(self, *, limit: int, page_size: int = 50) -> Iterator[SourcePeptideRecord]:
        """Yield individual sequence-bearing records from DBAASP pages.

        A list response is followed by the documented record-detail endpoint so
        activity conditions, termini, unusual residues, and chain-specific PDB
        references are not discarded.
        """

        if limit < 0:
            raise ValueError("limit cannot be negative")
        if limit == 0:
            return
        if not 1 <= page_size <= MAX_DBAASP_PAGE_SIZE:
            raise ValueError(f"page_size must be between 1 and {MAX_DBAASP_PAGE_SIZE}")

        emitted = 0
        offset = 0
        total_count: int | None = None
        while emitted < limit and (total_count is None or offset < total_count):
            response = self.http_client.get_json(self._page_url(limit=page_size, offset=offset), source=self.source_name)
            payload = response.payload
            if not isinstance(payload, Mapping):
                raise SourceRequestError(self.source_name, response.url, "expected an object response")
            rows = payload.get("data")
            if not isinstance(rows, list):
                raise SourceRequestError(self.source_name, response.url, "response did not contain a data list")
            total_count = _int_or_none(payload.get("totalCount"))
            if not rows:
                return

            for summary in rows:
                if not isinstance(summary, Mapping):
                    continue
                record_id = _int_or_none(summary.get("id"))
                if record_id is None:
                    continue
                detail_response = self.fetch_detail(record_id)
                detail = detail_response.payload
                if not isinstance(detail, Mapping):
                    raise SourceRequestError(self.source_name, detail_response.url, "expected an object detail response")
                for record in extract_dbaasp_peptide_records(
                    detail,
                    source_version=_source_version(detail_response),
                    retrieval_timestamp=detail_response.retrieved_at,
                ):
                    yield record
                    emitted += 1
                    if emitted >= limit:
                        return
            offset += len(rows)
            if len(rows) < page_size:
                return

    def fetch_detail(self, record_id: int) -> JsonResponse:
        if record_id < 1:
            raise ValueError("record_id must be positive")
        return self.http_client.get_json(f"{DBAASP_PEPTIDES_URL}/{record_id}", source=self.source_name)

    @staticmethod
    def _page_url(*, limit: int, offset: int) -> str:
        return f"{DBAASP_PEPTIDES_URL}?{urlencode({'limit': limit, 'offset': offset})}"


def extract_dbaasp_peptide_records(
    detail: Mapping[str, Any],
    *,
    source_version: str | None,
    retrieval_timestamp: str,
) -> list[SourcePeptideRecord]:
    """Turn a DBAASP detail record into sequence-bearing source occurrences."""

    parent_accession = _text(detail.get("dbaaspId")) or _dbaasp_accession(detail)
    monomers = detail.get("monomers")
    if isinstance(monomers, list) and monomers:
        records: list[SourcePeptideRecord] = []
        for monomer in monomers:
            if isinstance(monomer, Mapping):
                source_record = _make_record(
                    monomer,
                    parent=detail,
                    parent_accession=parent_accession,
                    source_version=source_version,
                    retrieval_timestamp=retrieval_timestamp,
                    is_component=True,
                )
                if source_record is not None:
                    records.append(source_record)
        return records

    record = _make_record(
        detail,
        parent=None,
        parent_accession=None,
        source_version=source_version,
        retrieval_timestamp=retrieval_timestamp,
        is_component=False,
    )
    return [record] if record is not None else []


def _make_record(
    record: Mapping[str, Any],
    *,
    parent: Mapping[str, Any] | None,
    parent_accession: str | None,
    source_version: str | None,
    retrieval_timestamp: str,
    is_component: bool,
) -> SourcePeptideRecord | None:
    sequence = _text(record.get("sequence"))
    if not sequence:
        return None

    record_id = _int_or_none(record.get("id"))
    source_accession = _text(record.get("dbaaspId")) or parent_accession or _dbaasp_accession(record)
    if not source_accession:
        return None
    source_record_key = _text(record.get("dbaaspId")) or f"{source_accession}:component:{record_id or sequence}"

    record_name = _text(record.get("name")) or _text(record.get("majorName")) or source_accession
    source_url = f"{DBAASP_PEPTIDES_URL}/{record_id}" if record_id is not None else DBAASP_PEPTIDES_URL
    activities = _experimental_properties(record)
    annotations = _annotations(record, parent=parent, is_component=is_component)
    modifications = _modifications(record, parent=parent)
    structure_references = _structure_references(record)

    return SourcePeptideRecord(
        sequence=sequence,
        source_database="DBAASP",
        source_accession=source_accession,
        source_url=source_url,
        source_record_key=source_record_key,
        name=record_name,
        parent_protein_accession=None,
        peptide_feature_coordinates=None,
        organism=_organism(record, parent=parent),
        description=_text(record.get("noteReference")),
        annotations=annotations,
        modifications=modifications,
        structure_references=structure_references,
        available_experimental_properties=activities,
        evidence_type=(
            "DBAASP experimentally annotated peptide record"
            if _has_activity_data(activities)
            else "DBAASP curated peptide record"
        ),
        source_version=source_version,
        retrieval_timestamp=retrieval_timestamp,
    )


def _annotations(
    record: Mapping[str, Any],
    *,
    parent: Mapping[str, Any] | None,
    is_component: bool,
) -> list[dict[str, Any]]:
    complexity = _name_or_text(record.get("complexity"))
    synthesis_type = _name_or_text(record.get("synthesisType"))
    annotation: dict[str, Any] = {
        "category": "DBAASP peptide record",
        "complexity": complexity,
        "synthesis_type": synthesis_type,
        "record_id": _int_or_none(record.get("id")),
    }
    annotations = [annotation]
    if is_component and parent is not None:
        annotations.append(
            {
                "category": "DBAASP parent complex",
                "parent_dbaasp_id": _text(parent.get("dbaaspId")),
                "parent_name": _text(parent.get("name")),
                "parent_complexity": _name_or_text(parent.get("complexity")),
                # A complex-level PDB reference is informative provenance but
                # is not represented as a chain-level peptide structure link.
                "parent_pdb_reference": _text(parent.get("pdb")),
            }
        )
    return annotations


def _experimental_properties(record: Mapping[str, Any]) -> dict[str, Any] | None:
    keys = (
        "targetActivities",
        "antibiofilmActivities",
        "hemoliticCytotoxicActivities",
        "synergies",
        "physicoChemicalProperties",
    )
    properties = {key: record[key] for key in keys if key in record and record[key] not in (None, [], {})}
    return properties or None


def _has_activity_data(properties: dict[str, Any] | None) -> bool:
    if not properties:
        return False
    return any(key in properties for key in ("targetActivities", "antibiofilmActivities", "hemoliticCytotoxicActivities"))


def _modifications(record: Mapping[str, Any], *, parent: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    fields = (
        "nTerminus",
        "cTerminus",
        "NTerminus",
        "CTerminus",
        "unusualAminoAcids",
        "intrachainBonds",
        "interchainBonds",
        "coordinationBonds",
    )
    modifications = [
        {"field": field, "value": record[field]}
        for field in fields
        if field in record and record[field] not in (None, "", [], {})
    ]
    if parent is not None:
        for field in ("interchainBonds", "coordinationBonds"):
            if field in parent and parent[field] not in (None, "", [], {}):
                modifications.append({"field": f"parent_{field}", "value": parent[field]})
    return modifications


def _structure_references(record: Mapping[str, Any]) -> list[dict[str, Any]]:
    references: list[dict[str, Any]] = []
    pdbs = record.get("pdbs")
    if isinstance(pdbs, list):
        for pdb in pdbs:
            if not isinstance(pdb, Mapping):
                continue
            pdb_id = _pdb_id(_text(pdb.get("name")) or _text(pdb.get("pdbUrl")))
            if pdb_id is None:
                continue
            references.append(
                {
                    "identifier": pdb_id,
                    "database": "RCSB PDB",
                    "pdb_id": pdb_id,
                    "url": _text(pdb.get("pdbUrl")) or f"https://www.rcsb.org/structure/{pdb_id}",
                    "source": "RCSB PDB",
                    "method": None,
                    "coordinate_file_url": _text(pdb.get("pdbFileUrl")),
                    "match_basis": "explicit DBAASP monomer PDB reference",
                }
            )
    return references


def _organism(record: Mapping[str, Any], *, parent: Mapping[str, Any] | None) -> str | None:
    for current in (record, parent):
        if current is None:
            continue
        genes = current.get("sourceGenes")
        if not isinstance(genes, list):
            continue
        for gene in genes:
            if isinstance(gene, Mapping):
                organism = _text(gene.get("source"))
                if organism:
                    return organism
    return None


def _source_version(response: JsonResponse) -> str | None:
    version = response.header("X-API-Version") or response.header("API-Version")
    return f"DBAASP API {version}" if version else None


def _pdb_id(value: str | None) -> str | None:
    if not value:
        return None
    match = re.search(r"(?<![A-Za-z0-9])([0-9][A-Za-z0-9]{3})(?:[_./?#]|$)", value)
    return match.group(1).upper() if match else None


def _dbaasp_accession(record: Mapping[str, Any]) -> str | None:
    record_id = _int_or_none(record.get("id"))
    return f"DBAASP_{record_id}" if record_id is not None else None


def _name_or_text(value: Any) -> str | None:
    if isinstance(value, Mapping):
        return _text(value.get("name")) or _text(value.get("description"))
    return _text(value)


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _text(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None
