"""Local API. Start with: python -m uvicorn backend.api:app --reload"""

import os
from functools import lru_cache

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .optimizer import optimize
from .schema import OptimizationRequest, OptimizationResult, PeptideLookupRequest
from .peptide_database import PeptideDatabase


app = FastAPI(title="Peptide Reference Lookup and Shape Optimization", version="0.2.0")
origins = os.getenv("PEPTIDE_CORS_ORIGINS", "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in origins.split(",") if origin.strip()],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/options")
def options():
    return {
        "default_request": OptimizationRequest().model_dump(),
        "methods": ["classical", "qaoa"],
        "sequence_length": {"min": 2, "max": 8},
        "maximum_torsions": 5,
        "energy_unit": "kcal/mol",
        "model": "MMFF94 discrete backbone torsion scan",
        "bit_order": "Rightmost bit controls the first torsion.",
        "peptide_lookup": {
            "endpoint": "/peptides/lookup",
            "sequence_length": {"min": 2, "max": 200},
            "status_endpoint": "/peptides/status",
        },
    }


@app.post("/optimize", response_model=OptimizationResult)
def optimize_peptide(request: OptimizationRequest):
    try:
        return optimize(request)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@lru_cache(maxsize=1)
def peptide_database():
    return PeptideDatabase()


@app.get("/peptides/status")
def peptide_catalog_status(database: PeptideDatabase = Depends(peptide_database)):
    return database.status()


@app.post("/peptides/lookup")
def lookup_peptide(request: PeptideLookupRequest, database: PeptideDatabase = Depends(peptide_database)):
    return database.lookup(request)
