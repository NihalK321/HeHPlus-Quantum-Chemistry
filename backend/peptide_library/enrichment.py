"""Identifier-gated external enrichers for stored peptide source records.

These enrichers never search by peptide name or approximate sequence. Callers
must supply an explicit PDB or ChEMBL identifier already present in trusted
source provenance.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from urllib.parse import urlencode
import re

from .http_client import JsonHttpClient, SourceRequestError


RCSB_ENTRY_URL = "https://data.rcsb.org/rest/v1/core/entry/{pdb_id}"
RCSB_PUBLIC_URL = "https://www.rcsb.org/structure/{pdb_id}"
CHEMBL_ACTIVITY_URL = "https://www.ebi.ac.uk/chembl/api/data/activity.json"

_PDB_ID_PATTERN = re.compile(r"^[0-9][A-Za-z0-9]{3}$")
_CHEMBL_ID_PATTERN = re.compile(r"^CHEMBL[0-9]+$", re.IGNORECASE)


class RcsbPdbEnricher:
    """Retrieve metadata for an explicit PDB identifier only."""

    source_name = "RCSB PDB"

    def __init__(self, http_client: JsonHttpClient | None = None) -> None:
        self.http_client = http_client or JsonHttpClient()

    def fetch_explicit_reference(self, pdb_id: str) -> dict[str, Any]:
        normalized_id = normalize_pdb_id(pdb_id)
        response = self.http_client.get_json(
            RCSB_ENTRY_URL.format(pdb_id=normalized_id),
            source=self.source_name,
        )
        if not isinstance(response.payload, Mapping):
            raise SourceRequestError(self.source_name, response.url, "expected an object response")

        entry = response.payload
        experimental_methods = entry.get("exptl")
        method = None
        if isinstance(experimental_methods, list) and experimental_methods:
            first_method = experimental_methods[0]
            if isinstance(first_method, Mapping) and isinstance(first_method.get("method"), str):
                method = first_method["method"]
        structure = entry.get("struct")
        title = structure.get("title") if isinstance(structure, Mapping) else None

        return {
            "database": self.source_name,
            "pdb_id": normalized_id,
            "url": RCSB_PUBLIC_URL.format(pdb_id=normalized_id),
            "entry_title": title if isinstance(title, str) else None,
            "experimental_method": method,
            "match_basis": "explicit source-supplied PDB identifier",
            "retrieved_at": response.retrieved_at,
        }

    def enrich_explicit_references(self, references: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Return references enriched only where a trusted explicit ID exists."""

        enriched: list[dict[str, Any]] = []
        for reference in references:
            copied_reference = dict(reference)
            raw_pdb_id = copied_reference.get("pdb_id")
            if not isinstance(raw_pdb_id, str):
                enriched.append(copied_reference)
                continue
            rcsb_metadata = self.fetch_explicit_reference(raw_pdb_id)
            copied_reference["rcsb_metadata"] = rcsb_metadata
            enriched.append(copied_reference)
        return enriched


class ChemblBioactivityEnricher:
    """Fetch ChEMBL bioactivity data only for a trusted stable ChEMBL ID."""

    source_name = "ChEMBL"

    def __init__(self, http_client: JsonHttpClient | None = None) -> None:
        self.http_client = http_client or JsonHttpClient()

    def fetch_bioactivities(self, chembl_id: str, *, limit: int = 100) -> dict[str, Any]:
        """Return raw assay-context data for an already verified identifier.

        This method intentionally rejects peptide names, accessions from other
        databases, and arbitrary small-molecule search terms.
        """

        normalized_id = normalize_chembl_id(chembl_id)
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        url = f"{CHEMBL_ACTIVITY_URL}?{urlencode({'molecule_chembl_id': normalized_id, 'limit': limit})}"
        response = self.http_client.get_json(url, source=self.source_name)
        if not isinstance(response.payload, Mapping):
            raise SourceRequestError(self.source_name, response.url, "expected an object response")
        activities = response.payload.get("activities")
        if not isinstance(activities, list):
            raise SourceRequestError(self.source_name, response.url, "response did not contain activities")
        return {
            "database": self.source_name,
            "chembl_id": normalized_id,
            "url": url,
            "activities": activities,
            "page_metadata": response.payload.get("page_meta"),
            "retrieved_at": response.retrieved_at,
            "match_basis": "trusted source-supplied ChEMBL identifier",
        }


def normalize_pdb_id(pdb_id: str) -> str:
    normalized_id = pdb_id.strip().upper()
    if not _PDB_ID_PATTERN.fullmatch(normalized_id):
        raise ValueError("pdb_id must be an explicit four-character PDB identifier")
    return normalized_id


def normalize_chembl_id(chembl_id: str) -> str:
    normalized_id = chembl_id.strip().upper()
    if not _CHEMBL_ID_PATTERN.fullmatch(normalized_id):
        raise ValueError("chembl_id must be an explicit stable CHEMBL identifier")
    return normalized_id
