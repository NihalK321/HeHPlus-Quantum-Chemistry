"""Read-only merged view of the original and additive peptide catalogs.

Neither source SQLite file is migrated, copied, or written.  Exact normalized
non-empty sequences identify one candidate record; source occurrences remain in
``sourceReferences``. Sequence-less compounds keep their stable catalog ID.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
import json
from math import ceil
from pathlib import Path
import sqlite3
from typing import Any, Protocol

from .extra_catalog import DEFAULT_DB


class PrimaryLibrary(Protocol):
    def search(self, **filters: Any) -> dict[str, Any]: ...


class CatalogUnavailableError(RuntimeError):
    """The optional local extra snapshot cannot be read without mutation."""


class CatalogDataError(RuntimeError):
    """A local catalog row does not have the documented data shape."""


def _text(value: Any, fallback: str = "") -> str:
    return value.strip() if isinstance(value, str) and value.strip() else fallback


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _items(value: Any) -> list[Any]:
    return list(value) if isinstance(value, (list, tuple)) else []


def _sequence(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    value = "".join(value.split()).upper()
    return value or None


def _append_unique(values: list[str], values_to_add: Iterable[str]) -> None:
    seen = {value.casefold() for value in values}
    for value in values_to_add:
        if value and value.casefold() not in seen:
            values.append(value)
            seen.add(value.casefold())


def _sorted_unique(values: Iterable[str]) -> list[str]:
    return sorted({value for value in values if value})


def _normalized_source_database(value: str) -> str:
    """``UniProtKB/Swiss-Prot`` and ``UniProtKB`` denote the same source here."""

    return value.casefold().replace("/swiss-prot", "").replace(" ", "")


def _coordinates_key(coordinates: Mapping[str, Any]) -> str:
    values: list[str] = []
    for field in ("featureId", "feature_id", "start", "end"):
        value = coordinates.get(field)
        values.append(str(value).strip() if value is not None else "")
    return ":".join(values)


def _source_key(reference: Mapping[str, Any]) -> str:
    coordinates = _mapping(reference.get("peptideFeatureCoordinates"))
    record_key = _text(reference.get("sourceRecordKey")) or _coordinates_key(coordinates)
    return "\x1f".join(
        (
            _normalized_source_database(_text(reference.get("sourceDatabase"))),
            _text(reference.get("sourceAccession")).casefold(),
            record_key.casefold(),
            _coordinates_key(coordinates),
        )
    )


def _extra_identity(record_id: str) -> tuple[str, str]:
    parts = record_id.split(":", 2)
    if len(parts) == 3 and parts[0].casefold() == "uniprot":
        return parts[1], parts[2]
    return "", record_id


def _primary_source(source: Mapping[str, Any], record_id: str) -> dict[str, Any]:
    coordinates = _mapping(source.get("peptideFeatureCoordinates"))
    source_key = _text(source.get("sourceRecordKey")) or _text(
        coordinates.get("featureId") or coordinates.get("feature_id")
    )
    return {
        "id": f"primary:{_text(source.get('id'), record_id)}",
        "catalogs": ["primary"],
        "catalogRecordIds": [f"primary:{record_id}"],
        "sourceDatabase": _text(source.get("sourceDatabase"), "Unavailable source"),
        "sourceAccession": _text(source.get("sourceAccession"), "Unavailable accession"),
        "sourceRecordKey": source_key,
        "sourceUrl": _text(source.get("sourceUrl")),
        "parentProteinAccession": source.get("parentProteinAccession"),
        "peptideFeatureCoordinates": dict(coordinates) if coordinates else None,
        "description": source.get("description"),
        "annotations": _items(source.get("annotations")),
        "modifications": _items(source.get("modifications")),
        "structureReferences": _items(source.get("structureReferences")),
        "availableExperimentalProperties": source.get("availableExperimentalProperties"),
        "evidenceType": source.get("evidenceType"),
        "sourceVersion": source.get("sourceVersion"),
        "retrievalTimestamp": source.get("retrievalTimestamp"),
        "provenance": "Original PepperQ peptide library",
    }


def _extra_sources(record: Mapping[str, Any]) -> list[dict[str, Any]]:
    record_id = _text(record.get("id"))
    parent_accession, feature_key = _extra_identity(record_id)
    raw_coordinates = _mapping(record.get("coordinates"))
    coordinates: dict[str, Any] | None = None
    if raw_coordinates:
        coordinates = {
            "start": raw_coordinates.get("start"),
            "end": raw_coordinates.get("end"),
            "coordinateSystem": "UniProt parent sequence; 1-based inclusive",
        }
        if feature_key != record_id:
            coordinates["featureId"] = feature_key
    exclusion = _text(record.get("exclusion_reason"))
    modifications = [{"description": exclusion}] if exclusion else []
    result: list[dict[str, Any]] = []
    for index, raw in enumerate(_items(record.get("source_references"))):
        reference = _mapping(raw)
        database = _text(reference.get("database"), "Extra catalog source")
        accession = _text(reference.get("accession")) or parent_accession or "Unavailable accession"
        result.append(
            {
                "id": f"extra:{record_id}:{index}",
                "catalogs": ["extra"],
                "catalogRecordIds": [f"extra:{record_id}"],
                "sourceDatabase": database,
                "sourceAccession": accession,
                "sourceRecordKey": feature_key if database.casefold().startswith("uniprot") else record_id,
                "sourceUrl": _text(reference.get("url")),
                "parentProteinAccession": parent_accession or None,
                "peptideFeatureCoordinates": coordinates,
                "description": record.get("provenance"),
                "annotations": _items(record.get("evidence")),
                "modifications": modifications,
                "structureReferences": [],
                "availableExperimentalProperties": None,
                "evidenceType": None,
                "sourceVersion": None,
                "retrievalTimestamp": None,
                "provenance": "Separate additive PepperQ catalog",
            }
        )
    return result


def _merge_sources(target: list[dict[str, Any]], additions: Iterable[dict[str, Any]]) -> None:
    known = {_source_key(value): value for value in target}
    for addition in additions:
        key = _source_key(addition)
        existing = known.get(key)
        if existing is None:
            target.append(addition)
            known[key] = addition
            continue
        existing["catalogs"] = _sorted_unique([*existing["catalogs"], *addition["catalogs"]])
        existing["catalogRecordIds"] = _sorted_unique(
            [*existing["catalogRecordIds"], *addition["catalogRecordIds"]]
        )
        for field in ("annotations", "modifications", "structureReferences"):
            values = existing.setdefault(field, [])
            fingerprints = {json.dumps(item, sort_keys=True, default=str) for item in values}
            for value in _items(addition.get(field)):
                fingerprint = json.dumps(value, sort_keys=True, default=str)
                if fingerprint not in fingerprints:
                    values.append(value)
                    fingerprints.add(fingerprint)


def _molecular_information(structure: Mapping[str, Any]) -> dict[str, Any] | None:
    if not structure:
        return None
    fields = {
        "formula": structure.get("formula"),
        "molecularWeightGmol": structure.get("molecular_weight_g_mol"),
        "smiles": structure.get("smiles"),
        "inchiKey": structure.get("inchi_key"),
        "chemblCanonicalSmiles": structure.get("chembl_canonical_smiles"),
    }
    return {key: value for key, value in fields.items() if value is not None}


def _group(
    *,
    identifier: str,
    name: str,
    sequence: str | None,
    kind: str,
    catalogs: Iterable[str],
    catalog_record_ids: Iterable[str],
    selectable: bool,
    scoring_eligible: bool,
    scoring_reason: str | None,
    modified: bool,
    sources: list[dict[str, Any]],
    aliases: Iterable[str] = (),
    molecular_info: Mapping[str, Any] | None = None,
    nonstandard_residues: Iterable[str] = (),
    notes: Iterable[str] = (),
) -> dict[str, Any]:
    normalized_aliases: list[str] = []
    _append_unique(normalized_aliases, aliases)
    normalized_aliases = [alias for alias in normalized_aliases if alias.casefold() != name.casefold()]
    return {
        "id": identifier,
        "name": name,
        "aliases": normalized_aliases,
        "kind": kind,
        "sequence": sequence,
        "sequenceLength": len(sequence) if sequence is not None else None,
        "nonstandardResidues": _sorted_unique(nonstandard_residues),
        "catalogs": _sorted_unique(catalogs),
        "catalogRecordIds": _sorted_unique(catalog_record_ids),
        "selectableForOptimization": selectable,
        "sequenceOnlyScoringEligible": scoring_eligible,
        "sequenceOnlyScoringExclusionReason": scoring_reason,
        "isChemicallyModified": modified,
        "molecularInformation": dict(molecular_info) if molecular_info else None,
        "sourceReferences": sources,
        "provenanceNotes": [value for value in notes if value],
    }


def _merge_group(target: dict[str, Any], incoming: dict[str, Any]) -> None:
    target["catalogs"] = _sorted_unique([*target["catalogs"], *incoming["catalogs"]])
    target["catalogRecordIds"] = _sorted_unique([*target["catalogRecordIds"], *incoming["catalogRecordIds"]])
    target["nonstandardResidues"] = _sorted_unique(
        [*target["nonstandardResidues"], *incoming["nonstandardResidues"]]
    )
    _append_unique(target["aliases"], [incoming["name"], *incoming["aliases"]])
    _append_unique(target["provenanceNotes"], incoming["provenanceNotes"])
    _merge_sources(target["sourceReferences"], incoming["sourceReferences"])
    target["selectableForOptimization"] = bool(
        target["selectableForOptimization"] or incoming["selectableForOptimization"]
    )
    target["sequenceOnlyScoringEligible"] = bool(
        target["sequenceOnlyScoringEligible"] or incoming["sequenceOnlyScoringEligible"]
    )
    target["isChemicallyModified"] = bool(target["isChemicallyModified"] or incoming["isChemicallyModified"])
    if target["molecularInformation"] is None and incoming["molecularInformation"] is not None:
        target["molecularInformation"] = incoming["molecularInformation"]
    if not target["sequenceOnlyScoringEligible"] and not target["sequenceOnlyScoringExclusionReason"]:
        target["sequenceOnlyScoringExclusionReason"] = incoming["sequenceOnlyScoringExclusionReason"]


class CatalogIntegrator:
    """Assemble an API view without replacing either existing catalog service."""

    def __init__(self, primary_library: PrimaryLibrary, extra_database_path: str | Path = DEFAULT_DB) -> None:
        self.primary_library = primary_library
        self.extra_database_path = Path(extra_database_path)

    def search(
        self,
        *,
        search: str | None = None,
        source: str | None = None,
        min_length: int | None = None,
        max_length: int | None = None,
        annotation: str | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> dict[str, Any]:
        self._validate(page, page_size, min_length, max_length)
        records, _ = self._records()
        matched = [
            record
            for record in records
            if self._matches(record, search, source, min_length, max_length, annotation)
        ]
        matched.sort(key=lambda record: (record["name"].casefold(), record["id"]))
        total = len(matched)
        start = (page - 1) * page_size
        return {
            "items": matched[start : start + page_size],
            "page": page,
            "pageSize": page_size,
            "total": total,
            "totalPages": ceil(total / page_size) if total else 0,
            "deduplication": {
                "method": "Exact normalized non-empty sequence identity; sequence-less records retain stable catalog IDs.",
                "sourceProvenance": "Source references are retained and deduplicated by database, accession, feature/record key, and coordinates.",
            },
        }

    def get(self, catalog_id: str) -> dict[str, Any] | None:
        records, _ = self._records()
        return next((record for record in records if record["id"] == catalog_id), None)

    def stats(self) -> dict[str, Any]:
        records, (primary, extra) = self._records()
        source_counts: Counter[str] = Counter()
        for record in records:
            for reference in record["sourceReferences"]:
                source_counts[reference["sourceDatabase"]] += 1
        return {
            "deduplicatedCandidateCount": len(records),
            "sequenceCandidateCount": sum(record["sequence"] is not None for record in records),
            "modifiedCandidateCount": sum(record["kind"] == "modified_peptide" for record in records),
            "rawCatalogRecordCount": len(primary) + len(extra),
            "originalCatalog": {
                "uniqueSequenceRecords": len(primary),
                "sourceRecordCount": sum(len(_items(record.get("sourceReferences"))) for record in primary),
            },
            "extraCatalog": {
                "rawRecordCount": len(extra),
                "uniqueNonNullSequenceCount": len({_sequence(record.get("sequence")) for record in extra} - {None}),
            },
            "bySource": dict(sorted(source_counts.items(), key=lambda item: item[0].casefold())),
            "deduplication": {
                "method": "Exact normalized non-empty sequence identity; sequence-less records retain stable catalog IDs.",
                "collapsedCatalogRecordCount": len(primary) + len(extra) - len(records),
                "note": "Raw catalog records are not presented as distinct candidate peptides.",
            },
        }

    def _records(self) -> tuple[list[dict[str, Any]], tuple[list[Mapping[str, Any]], list[Mapping[str, Any]]]]:
        primary = self._load_primary()
        extra = self._load_extra()
        groups: dict[str, dict[str, Any]] = {}
        for record in primary:
            normalized = self._from_primary(record)
            self._add(groups, normalized)
        for record in extra:
            normalized = self._from_extra(record)
            self._add(groups, normalized)
        return list(groups.values()), (primary, extra)

    @staticmethod
    def _add(groups: dict[str, dict[str, Any]], record: dict[str, Any]) -> None:
        current = groups.get(record["id"])
        if current is None:
            groups[record["id"]] = record
        else:
            _merge_group(current, record)

    def _load_primary(self) -> list[Mapping[str, Any]]:
        page, page_size = 1, 100
        output: list[Mapping[str, Any]] = []
        while True:
            response = self.primary_library.search(page=page, page_size=page_size)
            items = response.get("items")
            if not isinstance(items, list):
                raise CatalogDataError("Primary peptide library returned an invalid items collection.")
            output.extend(item for item in items if isinstance(item, Mapping))
            pages = response.get("totalPages")
            if not isinstance(pages, int):
                total = response.get("total")
                response_size = response.get("pageSize", page_size)
                pages = ceil(total / response_size) if isinstance(total, int) and response_size else page
            if page >= pages or not items:
                return output
            page += 1

    def _load_extra(self) -> list[Mapping[str, Any]]:
        path = self.extra_database_path.resolve()
        if not path.is_file():
            raise CatalogUnavailableError(
                f"The optional extra catalog is unavailable at {path}. Restore or import the documented local SQLite snapshot."
            )
        connection: sqlite3.Connection | None = None
        try:
            connection = sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True)
            rows = connection.execute("SELECT record_json FROM extra_peptides ORDER BY id").fetchall()
        except sqlite3.Error as error:
            raise CatalogDataError(f"The optional extra catalog has an unexpected schema: {error}") from error
        finally:
            if connection is not None:
                connection.close()
        output: list[Mapping[str, Any]] = []
        for index, (payload,) in enumerate(rows):
            try:
                record = json.loads(payload)
            except (TypeError, json.JSONDecodeError) as error:
                raise CatalogDataError(f"Extra catalog record {index} is not valid JSON.") from error
            if not isinstance(record, Mapping):
                raise CatalogDataError(f"Extra catalog record {index} is not a JSON object.")
            output.append(record)
        return output

    @staticmethod
    def _from_primary(record: Mapping[str, Any]) -> dict[str, Any]:
        record_id = _text(record.get("id"))
        if not record_id:
            raise CatalogDataError("Primary peptide record is missing its ID.")
        sequence = _sequence(record.get("sequence"))
        nonstandard = [str(value) for value in _items(record.get("nonstandardResidues")) if str(value)]
        selectable = bool(record.get("selectableForOptimization")) and sequence is not None and not nonstandard
        reason = None if selectable else "This imported record is not eligible for sequence-only scoring or candidate selection under its source validation flags."
        return _group(
            identifier=f"sequence:{sequence}" if sequence else f"primary:{record_id}",
            name=_text(record.get("name"), "Unnamed peptide"),
            sequence=sequence,
            kind="sequence_peptide",
            catalogs=["primary"],
            catalog_record_ids=[f"primary:{record_id}"],
            selectable=selectable,
            scoring_eligible=selectable,
            scoring_reason=reason,
            modified=False,
            sources=[_primary_source(value, record_id) for value in _items(record.get("sourceReferences")) if isinstance(value, Mapping)],
            aliases=[_text(record.get("name"))],
            nonstandard_residues=nonstandard,
            notes=["Original PepperQ peptide-library record"],
        )

    @staticmethod
    def _from_extra(record: Mapping[str, Any]) -> dict[str, Any]:
        record_id = _text(record.get("id"))
        if not record_id:
            raise CatalogDataError("Extra-catalog record is missing its ID.")
        sequence = _sequence(record.get("sequence"))
        kind = _text(record.get("kind"), "extra_catalog_record")
        exclusion = _text(record.get("exclusion_reason"))
        modified = kind == "modified_peptide" or bool(exclusion)
        selectable = bool(record.get("qaoa_sequence_supported")) and sequence is not None and not modified
        reason = exclusion or (None if selectable else "This record has no supported standard sequence for sequence-only chemistry scoring.")
        return _group(
            identifier=f"sequence:{sequence}" if sequence else f"extra:{record_id}",
            name=_text(record.get("name"), record_id),
            sequence=sequence,
            kind=kind,
            catalogs=["extra"],
            catalog_record_ids=[f"extra:{record_id}"],
            selectable=selectable,
            scoring_eligible=selectable,
            scoring_reason=reason,
            modified=modified,
            sources=_extra_sources(record),
            aliases=[_text(value) for value in _items(record.get("synonyms"))],
            molecular_info=_molecular_information(_mapping(record.get("structure"))),
            nonstandard_residues=(),
            notes=[_text(record.get("provenance")), _text(record.get("sequence_only_scoring_caveat"))],
        )

    @staticmethod
    def _validate(page: int, page_size: int, min_length: int | None, max_length: int | None) -> None:
        if page < 1:
            raise ValueError("page must be at least 1.")
        if page_size < 1 or page_size > 100:
            raise ValueError("page_size must be between 1 and 100.")
        if min_length is not None and min_length < 0:
            raise ValueError("min_length cannot be negative.")
        if max_length is not None and max_length < 0:
            raise ValueError("max_length cannot be negative.")
        if min_length is not None and max_length is not None and min_length > max_length:
            raise ValueError("min_length cannot exceed max_length.")

    @staticmethod
    def _matches(
        record: Mapping[str, Any],
        search: str | None,
        source: str | None,
        min_length: int | None,
        max_length: int | None,
        annotation: str | None,
    ) -> bool:
        length = record.get("sequenceLength")
        if min_length is not None and (not isinstance(length, int) or length < min_length):
            return False
        if max_length is not None and (not isinstance(length, int) or length > max_length):
            return False
        references = [_mapping(value) for value in _items(record.get("sourceReferences"))]
        if source and source.strip():
            needle = source.strip().casefold()
            if not any(needle in _text(reference.get("sourceDatabase")).casefold() for reference in references):
                return False
        if search and search.strip():
            needle = search.strip().casefold()
            haystack = [
                _text(record.get("id")), _text(record.get("name")), _text(record.get("sequence")),
                *(_text(value) for value in _items(record.get("aliases"))),
            ]
            for reference in references:
                haystack.extend((_text(reference.get("sourceDatabase")), _text(reference.get("sourceAccession")), _text(reference.get("sourceRecordKey")), _text(reference.get("description"))))
            if not any(needle in value.casefold() for value in haystack):
                return False
        if annotation and annotation.strip():
            needle = annotation.strip().casefold()
            blob = " ".join(json.dumps(reference.get("annotations", []), sort_keys=True, default=str) for reference in references)
            if needle not in blob.casefold():
                return False
        return True
