"""FastAPI routes for the local peptide-library SQLite database.

These routes query only locally imported records. They never accept an external
URL and never trigger a remote source import during a browser request.
"""

from __future__ import annotations

from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, Query

from .service import PeptideLibraryService, create_service


router = APIRouter()


@lru_cache(maxsize=1)
def get_peptide_library() -> PeptideLibraryService:
    return create_service()


@router.get("/peptides")
def list_peptides(
    search: str | None = Query(default=None, max_length=200, description="Name or sequence fragment."),
    name: str | None = Query(default=None, max_length=200, description="Name fragment alias."),
    sequence: str | None = Query(default=None, max_length=200, description="Sequence fragment alias."),
    source: str | None = Query(default=None, max_length=100),
    min_length: int | None = Query(default=None, ge=0),
    max_length: int | None = Query(default=None, ge=0),
    annotation: str | None = Query(default=None, max_length=200),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    library: PeptideLibraryService = Depends(get_peptide_library),
):
    """Search already imported peptide records with bounded pagination."""

    aliases = [value.strip() for value in (search, name, sequence) if value and value.strip()]
    if len(set(aliases)) > 1:
        raise HTTPException(
            status_code=422,
            detail="Use one of search, name, or sequence per request; each searches imported names and sequences.",
        )
    try:
        return library.search(
            search=aliases[0] if aliases else None,
            source=source,
            minimum_length=min_length,
            maximum_length=max_length,
            annotation=annotation,
            page=page,
            page_size=page_size,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get("/peptides/stats")
def peptide_stats(library: PeptideLibraryService = Depends(get_peptide_library)):
    """Return actual local SQLite counts; no source API is contacted."""

    raw_stats = library.stats()
    by_source = {
        item["sourceDatabase"]: item["recordCount"]
        for item in raw_stats["bySource"]
    }
    return {
        "totalPeptides": raw_stats["totalImportedRecords"],
        "totalImportedRecords": raw_stats["totalImportedRecords"],
        "totalSourceRecords": raw_stats["totalSourceRecords"],
        "bySource": by_source,
        "withStructures": raw_stats["withStructures"],
        "withExperimentalAnnotations": raw_stats["withExperimentalAnnotations"],
    }


@router.get("/peptides/{peptide_id}")
def get_peptide(
    peptide_id: str,
    library: PeptideLibraryService = Depends(get_peptide_library),
):
    """Return one complete local record and every retained source reference."""

    record = library.get(peptide_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Peptide record not found.")
    return record
