# Peptide shape-search backend

This backend implements a small **fixed-sequence conformation search**. It does
not optimize amino-acid identity or predict biological effects. The existing
peptide lookup code remains separate in `class_computing_`.

## Run

From the `Peptide-Project` directory with your virtual environment active:

```powershell
python -m pip install -r backend/requirements.txt
python -m uvicorn backend.api:app --reload
```

Open http://127.0.0.1:8000/docs for interactive request/response documentation.
No IBM account or credentials are needed. The server binds locally by default.

```powershell
python -m pytest backend/test_backend.py -q
```

## Frontend contract

- `GET /health`: returns `{"status": "ok"}`.
- `GET /options`: supported limits, defaults, and units.
- `POST /optimize`: run classical enumeration or QAOA simulation.
- Invalid requests or unsupported molecular geometry return HTTP 422 and a
  `detail` field. An unsuccessful optimizer convergence status is returned in
  a normal result; inspect `optimizer_converged` and `optimizer_message`.

Example JSON body:

```json
{
  "sequence": "GAGA",
  "method": "qaoa",
  "torsion_count": 3,
  "angle_options": [-60, 120],
  "seed": 42,
  "layers": 1,
  "max_iterations": 60,
  "shots": 1024
}
```

Use `"method": "classical"` to get the exact reference minimum. Other fields
have the defaults shown above. Sequences contain 2–8 standard one-letter codes;
requests scan 1–5 supported backbone torsions (at most 32 configurations).
A short peptide may have fewer available torsions; reduce `torsion_count` if
the API reports that. Proline ring bonds are excluded from rotation.

Key response fields:

| Field | Frontend use |
| --- | --- |
| `torsions`, `angle_options` | Explain which shape decisions are varied |
| `configurations` | Plot every configuration's MMFF94 energy in kcal/mol |
| `best_configuration` | Show the classical minimum or lowest-energy sampled QAOA outcome |
| `best_structure_molblock` | Load the selected 3D structure into a molecular viewer |
| `probabilities` | Plot the ideal circuit distribution (classical mode: equal mass on exact optima) |
| `counts` | Plot sampled circuit outcomes; empty for classical enumeration |
| `benchmark` | Exact minimum, energy gap, and optimum probabilities versus uniform sampling |
| `optimizer_converged`, `optimizer_message` | Show convergence or iteration-limit status |
| `limitations` | Explain the scope of the experiment |

Bitstrings follow Qiskit ordering: the **rightmost** bit controls the **first**
torsion. For example, `001` selects angle option 1 for torsion 0, and option 0
for the other torsions. Each configuration includes decoded angles.

The default CORS origins cover localhost and 127.0.0.1 on ports 3000 and 5173.
Set `PEPTIDE_CORS_ORIGINS` to a comma-separated list to use another frontend.

## Python entry point

```python
from backend.optimizer import optimize
from backend.schema import OptimizationRequest

result = optimize(OptimizationRequest(sequence="GAGA", method="classical"))
print(result.best_configuration)
print(result.benchmark)
```

## Responsibilities

- `schema.py`: validated inputs and JSON response models.
- `chemistry.py`: RDKit molecule creation, torsion selection, geometry and energy table.
- `quantum.py`: exact diagonal cost Hamiltonian/circuit and ideal QAOA probabilities.
- `optimizer.py`: classical search or SciPy parameter optimization of Qiskit circuits.
- `benchmark.py`: comparisons against exhaustive enumeration and uniform sampling.
- `api.py`: HTTP endpoints and local frontend CORS settings.

## Scientific scope

RDKit constructs a linear peptide with free termini and its default protonation,
embeds an ETKDGv3 starting geometry using the seed, and selects the first available
non-ring phi/psi backbone torsions in residue order. Every selected torsion has
two allowed angles. All other coordinates remain fixed, with no relaxation,
solvent, disulfide bridges, or additional chemical modifications. High-energy
clashing shapes remain in the table with their calculated energies.

The reported minimum is only the best **within this discrete grid**. MMFF94 is
classical molecular mechanics, not quantum electronic structure or a prediction
of a peptide's native structure. Absolute energies must not be compared across
different sequences. The chemistry challenge rubric may require a different
model; keep that eligibility question separate from whether the software works.

Both methods use a classically enumerated energy table. QAOA scales the table to
[0, 1] for its cost phase, then minimizes the expected scaled energy with COBYLA.
It uses an exact diagonal unitary, allowing higher-order interactions rather
than assuming the energy is quadratic. Displayed energies use the original units.
The final ideal probabilities are sampled with a seeded random generator.
Expectation and optimum probability come from the ideal distribution, while the
best observed configuration and its gap come from those finite samples.

There is no hardware noise, error mitigation, or speedup claim. Larger peptides,
broader torsion scans, and electronic-structure calculations are future work.

## Implementation references

- [RDKit peptide construction](https://www.rdkit.org/docs/source/rdkit.Chem.rdmolfiles.html)
- [RDKit dihedral transformations](https://rdkit.org/docs/source/rdkit.Chem.rdMolTransforms.html)
- [RDKit force fields](https://rdkit.org/docs/source/rdkit.ForceField.rdForceField.html)
- [Peptide conformational sampling with QAOA (motivation, not a reproduced implementation)](https://www.nature.com/articles/s41534-023-00733-5)
- [FastAPI testing](https://fastapi.tiangolo.com/tutorial/testing/)

## Large known-peptide sequence catalog

`peptide_database.py` imports paginated peptide summaries from **DBAASP** into a
local SQLite index. It keeps uppercase standard-amino-acid single-chain
sequences of length 2–200. Multichain entries, lowercase residue encodings, and
nonstandard residue codes are skipped rather than changed. Distinct source
records sharing one sequence remain separate because their modifications and
assays can differ. The original local sequence references are also included.
Name-only references requiring nonstandard residues are not sequence-searchable.

DBAASP focuses on antimicrobial and cytotoxic peptides; this is not a universal
database of all peptides, hormones, or GLP-1 analogues. Indexing a sequence does
not verify stereochemistry, terminal modifications, or other chemical features.

Download or refresh the catalog from the repository root:

```powershell
python -m backend.peptide_database sync
python -m backend.peptide_database status
```

Sync requires internet and can take several minutes. Failed downloads preserve
the previous catalog. Data is stored in `backend/.peptide_cache/catalog.sqlite3`,
which is excluded from Git. Teammates should run the sync command on their own
machines. `PEPTIDE_DATABASE_PATH` can select a different SQLite file. The API
never silently downloads the entire source database during a lookup.

- `GET /peptides/status`: actual indexed record count, source counts, and sync timestamp.
- `POST /peptides/lookup`: complete sequence matches, optionally similar sequences.

Example lookup body:

```json
{
  "sequence": "ENREVPPGFTALIKTLRKCKII",
  "limit": 5,
  "include_similar": true,
  "minimum_identity": 0.7,
  "include_details": true
}
```

Lookup accepts longer peptides than the shape optimizer, up to 200 residues.
`exact_match_count` is the full count; `exact_matches` contains at most `limit`
records. Exact matches mean **backbone sequence matches**, not verified molecular
identity. With details enabled, uncached exact DBAASP hits fetch source assay
measurements (concentration, units, target, medium, and notes), structural
annotations, and article references. These fields describe experiments on the
reference peptide, not effects predicted for the user's molecule. At most 20
activity rows per category are returned, with a truncation flag if needed.

`include_details: false` uses only local data, so it works offline after sync.
Previously fetched details are also cached; their retrieval timestamp is
returned. A new sync clears that detail cache. An unavailable source is reported
in `detail_status` without turning an existing sequence match into a false miss.

Optional similarities compare aligned positions in **equal-length sequences**.
For example, 4 identical positions out of 5 gives `sequence_identity: 0.8`.
This is not BLAST, an activity prediction, or a probability of shared effects.
Similarity results do not copy the known peptide's role onto the input sequence.
The response includes interpretation notes and source attribution.

Test the catalog integration without network access:

```powershell
python -m pytest backend/test_peptide_database.py -q
```

Backend tests use unique project-local temporary directories, automatically
cleaned after each test, to avoid permission conflicts in Windows's shared
`pytest-of-<user>` temporary folder. These directories are excluded from Git.

DBAASP data is openly usable with acknowledgement under its
[data usage policy](https://www.dbaasp.org/terms-and-conditions). Acknowledge
DBAASP in your project and presentation and cite
[Pirtskhalava et al., DBAASP v3](https://doi.org/10.1093/nar/gkaa991).
The source API is documented at https://www.dbaasp.org/api?page=rest.
