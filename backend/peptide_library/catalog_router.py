"""FastAPI routes for the read-only merged PepperQ peptide catalog."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from .api_router import get_peptide_library
from .catalog_integration import CatalogDataError, CatalogIntegrator, CatalogUnavailableError
from .service import PeptideLibraryService


router = APIRouter(prefix="/peptide-catalog", tags=["Merged peptide catalog"])


def get_catalog_integrator(
    library: PeptideLibraryService = Depends(get_peptide_library),
) -> CatalogIntegrator:
    """Construct a request-local adapter; neither source catalog is changed."""

    return CatalogIntegrator(library)


def _http_error(error: Exception) -> HTTPException:
    if isinstance(error, CatalogUnavailableError):
        return HTTPException(status_code=503, detail=str(error))
    if isinstance(error, (CatalogDataError, ValueError)):
        return HTTPException(status_code=422, detail=str(error))
    return HTTPException(status_code=500, detail="The merged peptide catalog could not be assembled.")


@router.get("")
def list_catalog(
    search: str | None = Query(default=None, max_length=200),
    source: str | None = Query(default=None, max_length=100),
    min_length: int | None = Query(default=None, ge=0),
    max_length: int | None = Query(default=None, ge=0),
    annotation: str | None = Query(default=None, max_length=200),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    catalog: CatalogIntegrator = Depends(get_catalog_integrator),
):
    """Search globally deduplicated candidates from both local catalogs."""

    try:
        return catalog.search(
            search=search,
            source=source,
            min_length=min_length,
            max_length=max_length,
            annotation=annotation,
            page=page,
            page_size=page_size,
        )
    except Exception as error:
        raise _http_error(error) from error


@router.get("/stats")
def catalog_stats(catalog: CatalogIntegrator = Depends(get_catalog_integrator)):
    """Report raw rows separately from deduplicated candidate records."""

    try:
        return catalog.stats()
    except Exception as error:
        raise _http_error(error) from error


@router.get("/{catalog_id:path}")
def get_catalog_record(catalog_id: str, catalog: CatalogIntegrator = Depends(get_catalog_integrator)):
    """Return one merged record with source provenance and molecular metadata."""

    if len(catalog_id) > 600:
        raise HTTPException(status_code=400, detail="Invalid catalog record ID.")
    try:
        record = catalog.get(catalog_id)
    except Exception as error:
        raise _http_error(error) from error
    if record is None:
        raise HTTPException(status_code=404, detail="Merged peptide catalog record not found.")
    return record
