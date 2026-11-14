"""Optional FastAPI router for the additive catalog; safe to mount after Codex finishes.

Add to backend/api.py (after confirming file ownership):
    from backend.peptide_library.extra_api import router as peptide_extras_router
    app.include_router(peptide_extras_router)

Run FastAPI from the project root so imports resolve normally.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from .extra_catalog import DEFAULT_DB, get_record, get_stats, open_db, search_records

router = APIRouter(prefix="/api/peptide-extras", tags=["Peptide Extras"])

@router.get("")
def extras_search(q: str = Query("", max_length=100), limit: int = Query(25, ge=1, le=100),
                  offset: int = Query(0, ge=0)):
    with open_db(DEFAULT_DB) as db:
        return search_records(db, q, limit, offset)

@router.get("/stats")
def extras_stats():
    with open_db(DEFAULT_DB) as db:
        return get_stats(db)

@router.get("/{record_id:path}")
def extras_detail(record_id: str):
    if len(record_id) > 200:
        raise HTTPException(status_code=400, detail="Invalid record ID")
    with open_db(DEFAULT_DB) as db:
        result = get_record(db, record_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Record not found")
    return result
