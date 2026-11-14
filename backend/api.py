"""Local API. Start with: python -m uvicorn backend.api:app --reload"""

import os
from functools import lru_cache

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

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
    expose_headers=["Content-Disposition"],
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


def _pdb_download(result: OptimizationResult) -> Response:
    filename = f"peptide_{result.sequence}_{result.method}_{result.best_configuration.bitstring}.pdb"
    return Response(
        content=result.best_structure_pdb,
        media_type="chemical/x-pdb",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/structure.pdb", response_class=Response,
         responses={200: {"content": {"chemical/x-pdb": {}}, "description": "Download the classical best configuration as PDB."}})
def download_structure(sequence: str = "GAGA", torsion_count: int = 3, seed: int = 42):
    """Browser-friendly download using the default angles and classical search."""
    try:
        request = OptimizationRequest(sequence=sequence, torsion_count=torsion_count, seed=seed)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return _pdb_download(optimize_peptide(request))


@app.post("/optimize/pdb", response_class=Response,
          responses={200: {"content": {"chemical/x-pdb": {}}, "description": "Download the selected optimized configuration as PDB."}})
def optimize_peptide_pdb(request: OptimizationRequest):
    """Accept the same settings as /optimize, including QAOA and custom angles."""
    return _pdb_download(optimize_peptide(request))


@lru_cache(maxsize=1)
def peptide_database():
    return PeptideDatabase()


@app.get("/peptides/status")
def peptide_catalog_status(database: PeptideDatabase = Depends(peptide_database)):
    return database.status()


@app.post("/peptides/lookup")
def lookup_peptide(request: PeptideLookupRequest, database: PeptideDatabase = Depends(peptide_database)):
    return database.lookup(request)
