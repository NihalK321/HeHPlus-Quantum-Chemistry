"""UniProtKB connector for annotated mature peptide features.

This connector deliberately imports only ``Peptide`` features returned by
UniProtKB. It never treats a parent precursor sequence or a generic ``Chain``
feature as a mature peptide record.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import Any
from urllib.parse import urlencode, urlparse
import re

from .http_client import JsonHttpClient, JsonResponse, SourceRequestError
from .models import SourcePeptideRecord


UNIPROT_SEARCH_URL = "https://rest.uniprot.org/uniprotkb/search"
UNIPROT_ENTRY_URL = "https://www.uniprot.org/uniprotkb/{accession}"
UNIPROT_QUERY = "reviewed:true AND ft_peptide:*"
MAX_UNIPROT_PAGE_SIZE = 500

_MODIFICATION_FEATURE_TYPES = {
    "modified residue",
    "non-standard residue",
    "lipidation",
    "glycosylation",
    "cross-link",
}


class UniProtPeptideConnector:
    """Fetch reviewed UniProtKB entries and extract explicitly annotated peptides."""

    source_name = "UniProt"

    def __init__(self, http_client: JsonHttpClient | None = None) -> None:
        self.http_client = http_client or JsonHttpClient()

    def iter_mature_peptides(
        self,
        *,
        limit: int,
        page_size: int = MAX_UNIPROT_PAGE_SIZE,
        query: str = UNIPROT_QUERY,
    ) -> Iterator[SourcePeptideRecord]:
        """Yield up to ``limit`` real peptide-feature records.

        Cursor URLs are taken from UniProt's ``Link`` header rather than being
        constructed locally. This avoids accidental pagination omissions when
        UniProt changes its cursor format.
        """

        if limit < 0:
            raise ValueError("limit cannot be negative")
        if limit == 0:
            return
        if not 1 <= page_size <= MAX_UNIPROT_PAGE_SIZE:
            raise ValueError(f"page_size must be between 1 and {MAX_UNIPROT_PAGE_SIZE}")

        next_url = self._search_url(query=query, page_size=page_size)
        emitted = 0
        while next_url and emitted < limit:
            response = self.http_client.get_json(next_url, source=self.source_name)
            payload = response.payload
            if not isinstance(payload, Mapping):
                raise SourceRequestError(self.source_name, next_url, "expected an object response")

            entries = payload.get("results")
            if not isinstance(entries, list):
                raise SourceRequestError(self.source_name, next_url, "response did not contain a results list")

            source_version = _source_version(response)
            for entry in entries:
                if not isinstance(entry, Mapping):
                    continue
                for record in extract_mature_peptide_records(
                    entry,
                    source_version=source_version,
                    retrieval_timestamp=response.retrieved_at,
                ):
                    yield record
                    emitted += 1
                    if emitted >= limit:
                        return

            next_url = parse_next_link(response.header("Link"))
            if next_url and urlparse(next_url).netloc != urlparse(UNIPROT_SEARCH_URL).netloc:
                raise SourceRequestError(self.source_name, next_url, "pagination link did not target the UniProt REST host")

    @staticmethod
    def _search_url(*, query: str, page_size: int) -> str:
        parameters = {
            "query": query,
            "format": "json",
            "size": str(page_size),
            # Asking for feature columns makes UniProt include the feature table
            # needed for exact parent-coordinate extraction.
            "fields": ",".join(
                (
                    "accession",
                    "id",
                    "protein_name",
                    "organism_name",
                    "sequence",
                    "ft_peptide",
                    "ft_mod_res",
                    "ft_non_std",
                    "ft_lipid",
                    "ft_carbohyd",
                    "ft_crosslnk",
                )
            ),
        }
        return f"{UNIPROT_SEARCH_URL}?{urlencode(parameters)}"


def extract_mature_peptide_records(
    entry: Mapping[str, Any],
    *,
    source_version: str | None,
    retrieval_timestamp: str,
) -> list[SourcePeptideRecord]:
    """Extract peptide features using UniProt's 1-based, inclusive positions.

    Features with unknown, fuzzy, incomplete, or out-of-range endpoints are
    skipped. Guessing a cleavage position would fabricate a peptide sequence.
    """

    accession = _text(entry.get("primaryAccession"))
    parent_sequence = _text(_mapping(entry.get("sequence")).get("value"))
    if not accession or not parent_sequence:
        return []

    parent_name = _protein_name(entry) or accession
    organism = _text(_mapping(entry.get("organism")).get("scientificName"))
    features = entry.get("features")
    if not isinstance(features, list):
        return []

    records: list[SourcePeptideRecord] = []
    for feature in features:
        if not isinstance(feature, Mapping) or _text(feature.get("type")) != "Peptide":
            continue

        coordinates = _exact_coordinates(feature.get("location"), sequence_length=len(parent_sequence))
        if coordinates is None:
            continue
        start, end = coordinates
        sequence = parent_sequence[start - 1 : end]
        if not sequence:
            continue

        feature_id = _text(feature.get("featureId")) or f"{accession}:{start}-{end}"
        description = _text(feature.get("description"))
        peptide_name = description or f"{parent_name} peptide {start}-{end}"
        peptide_coordinates = {
            "start": start,
            "end": end,
            "coordinate_system": "UniProt parent sequence; 1-based inclusive",
            "feature_id": feature_id,
        }
        annotations: list[dict[str, Any]] = [
            {
                "category": "UniProt feature",
                "type": "Peptide",
                "description": description,
                "feature_id": feature_id,
                "coordinates": peptide_coordinates,
                "evidence": _list_of_mappings(feature.get("evidences")),
            }
        ]

        records.append(
            SourcePeptideRecord(
                sequence=sequence,
                source_database="UniProtKB/Swiss-Prot",
                source_accession=accession,
                source_url=UNIPROT_ENTRY_URL.format(accession=accession),
                source_record_key=feature_id,
                name=peptide_name,
                parent_protein_accession=accession,
                peptide_feature_coordinates=peptide_coordinates,
                organism=organism,
                description=description,
                annotations=annotations,
                modifications=_overlapping_modifications(features, start=start, end=end),
                structure_references=[],
                available_experimental_properties=None,
                evidence_type="UniProtKB curated peptide feature",
                source_version=source_version,
                retrieval_timestamp=retrieval_timestamp,
            )
        )
    return records


def parse_next_link(link_header: str | None) -> str | None:
    """Return the ``rel=next`` URL from an RFC 8288 Link header."""

    if not link_header:
        return None
    # UniProt's `fields` query parameter contains literal commas. Splitting a
    # Link header on commas would therefore corrupt the URL before `rel=next`.
    match = re.search(r'<([^>]+)>\s*;\s*rel="?next"?(?:\s|,|$)', link_header)
    return match.group(1) if match else None


def _source_version(response: JsonResponse) -> str | None:
    release = response.header("X-UniProt-Release")
    release_date = response.header("X-UniProt-Release-Date")
    if release and release_date:
        return f"UniProt release {release} ({release_date})"
    if release:
        return f"UniProt release {release}"
    return None


def _overlapping_modifications(features: list[Any], *, start: int, end: int) -> list[dict[str, Any]]:
    modifications: list[dict[str, Any]] = []
    for feature in features:
        if not isinstance(feature, Mapping):
            continue
        feature_type = _text(feature.get("type"))
        if feature_type is None or feature_type.casefold() not in _MODIFICATION_FEATURE_TYPES:
            continue
        coordinates = _exact_coordinates(feature.get("location"), sequence_length=None)
        if coordinates is None:
            continue
        feature_start, feature_end = coordinates
        if feature_end < start or feature_start > end:
            continue
        modifications.append(
            {
                "type": feature_type,
                "description": _text(feature.get("description")),
                "feature_id": _text(feature.get("featureId")),
                "coordinates": {
                    "start": feature_start,
                    "end": feature_end,
                    "coordinate_system": "UniProt parent sequence; 1-based inclusive",
                },
                "evidence": _list_of_mappings(feature.get("evidences")),
            }
        )
    return modifications


def _exact_coordinates(location: Any, *, sequence_length: int | None) -> tuple[int, int] | None:
    location_mapping = _mapping(location)
    start_mapping = _mapping(location_mapping.get("start"))
    end_mapping = _mapping(location_mapping.get("end"))
    if not start_mapping or not end_mapping:
        return None
    if _text(start_mapping.get("modifier"), default="EXACT") != "EXACT":
        return None
    if _text(end_mapping.get("modifier"), default="EXACT") != "EXACT":
        return None

    try:
        start = int(start_mapping["value"])
        end = int(end_mapping["value"])
    except (KeyError, TypeError, ValueError):
        return None
    if start < 1 or end < start:
        return None
    if sequence_length is not None and end > sequence_length:
        return None
    return start, end


def _protein_name(entry: Mapping[str, Any]) -> str | None:
    description = _mapping(entry.get("proteinDescription"))
    for key in ("recommendedName", "submissionNames", "alternativeNames"):
        value = description.get(key)
        candidates = value if isinstance(value, list) else [value]
        for candidate in candidates:
            full_name = _mapping(_mapping(candidate).get("fullName"))
            name = _text(full_name.get("value"))
            if name:
                return name
    return None


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _list_of_mappings(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)]


def _text(value: Any, *, default: str | None = None) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or default
    return default
