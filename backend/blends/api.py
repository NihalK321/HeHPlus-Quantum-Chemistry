"""Versioned, local-only blend-research endpoints."""

from functools import lru_cache
from fastapi import APIRouter, Depends, HTTPException, Query

from .catalog import BlendCatalog
from .models import BlendRequest, ShortlistRequest
from .solver import optimize_blend, shortlist


router = APIRouter(prefix="/blends", tags=["Blend research v1"])


@lru_cache(maxsize=1)
def get_blend_catalog():
    return BlendCatalog()


@router.get("/catalog")
def browse_catalog(search: str = Query(default="", max_length=200), page: int = Query(default=1, ge=1),
                   page_size: int = Query(default=20, ge=1, le=50), catalog=Depends(get_blend_catalog)):
    return catalog.search(search, page, page_size)


@router.post("/shortlist")
def shortlist_candidates(request: ShortlistRequest, catalog=Depends(get_blend_catalog)):
    return shortlist(catalog, request)


@router.post("/optimize")
def run_blend_qaoa(request: BlendRequest, catalog=Depends(get_blend_catalog)):
    try:
        return optimize_blend(catalog, request)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
