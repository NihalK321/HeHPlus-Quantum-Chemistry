"""Application service for importing and querying provenance-rich peptides."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any, Iterable

from .dbaasp import DbaaspPeptideConnector
from .enrichment import ChemblBioactivityEnricher, RcsbPdbEnricher
from .http_client import SourceRequestError
from .models import SourcePeptideRecord
from .storage import PeptideRepository
from .uniprot import UniProtPeptideConnector


@dataclass(slots=True)
class ImportReport:
    """Transparent outcome for one source-import attempt."""

    source: str
    requested_limit: int
    processed_records: int = 0
    created_peptides: int = 0
    created_source_references: int = 0
    skipped_records: int = 0
    failed_records: int = 0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def status(self) -> str:
        if self.failed_records:
            return "partial" if self.processed_records else "failed"
        return "completed"

    def to_dict(self, *, database_stats: dict[str, Any]) -> dict[str, Any]:
        return {
            **asdict(self),
            "status": self.status,
            "database": database_stats,
        }


class PeptideLibraryService:
    """Coordinates source connectors, normalization, SQLite, and safe enrichment."""

    def __init__(self, repository: PeptideRepository | None = None) -> None:
        self.repository = repository or PeptideRepository()
        self.repository.initialize()

    def import_uniprot(
        self,
        *,
        limit: int,
        page_size: int = 500,
        connector: UniProtPeptideConnector | None = None,
    ) -> dict[str, Any]:
        active_connector = connector or UniProtPeptideConnector()
        report = ImportReport(source="UniProtKB/Swiss-Prot", requested_limit=limit)
        self._store_records(
            active_connector.iter_mature_peptides(limit=limit, page_size=page_size),
            report,
        )
        return report.to_dict(database_stats=self.repository.stats())

    def import_dbaasp(
        self,
        *,
        limit: int,
        page_size: int = 50,
        enrich_structures: bool = False,
        connector: DbaaspPeptideConnector | None = None,
        rcsb_enricher: RcsbPdbEnricher | None = None,
    ) -> dict[str, Any]:
        active_connector = connector or DbaaspPeptideConnector()
        report = ImportReport(source="DBAASP", requested_limit=limit)
        records: Iterable[SourcePeptideRecord] = active_connector.iter_peptides(limit=limit, page_size=page_size)
        if enrich_structures:
            records = self._enrich_structure_records(records, report, rcsb_enricher or RcsbPdbEnricher())
        self._store_records(records, report)
        return report.to_dict(database_stats=self.repository.stats())

    def search(self, **filters: Any) -> dict[str, Any]:
        return self.repository.search(**filters)

    def get(self, peptide_id: str) -> dict[str, Any] | None:
        return self.repository.get(peptide_id)

    def stats(self) -> dict[str, Any]:
        return self.repository.stats()

    @staticmethod
    def fetch_trusted_chembl_bioactivities(chembl_id: str) -> dict[str, Any]:
        """Keep ChEMBL gated behind a trusted source-supplied identifier."""

        return ChemblBioactivityEnricher().fetch_bioactivities(chembl_id)

    def _store_records(self, records: Iterable[SourcePeptideRecord], report: ImportReport) -> None:
        try:
            for record in records:
                try:
                    outcome = self.repository.upsert(record)
                except ValueError as error:
                    report.skipped_records += 1
                    report.warnings.append(f"Skipped {record.source_database} {record.source_record_key}: {error}")
                    continue

                report.processed_records += 1
                report.created_peptides += int(outcome.peptide_created)
                report.created_source_references += int(outcome.source_reference_created)
        except SourceRequestError as error:
            report.failed_records += 1
            report.errors.append(str(error))

    @staticmethod
    def _enrich_structure_records(
        records: Iterable[SourcePeptideRecord],
        report: ImportReport,
        enricher: RcsbPdbEnricher,
    ) -> Iterable[SourcePeptideRecord]:
        for record in records:
            references: list[dict[str, Any]] = []
            for reference in record.structure_references:
                enriched_reference = dict(reference)
                pdb_id = enriched_reference.get("pdb_id")
                if isinstance(pdb_id, str):
                    try:
                        metadata = enricher.fetch_explicit_reference(pdb_id)
                    except (SourceRequestError, ValueError) as error:
                        report.warnings.append(
                            f"Could not enrich explicit PDB reference {pdb_id} for {record.source_record_key}: {error}"
                        )
                    else:
                        enriched_reference["method"] = metadata.get("experimental_method")
                        enriched_reference["entryTitle"] = metadata.get("entry_title")
                        enriched_reference["enrichedAt"] = metadata.get("retrieved_at")
                        enriched_reference["matchBasis"] = metadata.get("match_basis")
                references.append(enriched_reference)
            yield replace(record, structure_references=references)


def create_service(database_path: str | Path | None = None) -> PeptideLibraryService:
    """Factory kept separate so API tests can substitute an isolated database."""

    return PeptideLibraryService(PeptideRepository(database_path))
