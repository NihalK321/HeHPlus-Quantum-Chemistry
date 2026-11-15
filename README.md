# IBM Qiskit Fall Fest 2026 — HeH+ potential-energy curve

This is a standalone quantum-chemistry submission for the IBM challenge. It
does not use the peptide/QAOA portions of PepperQ.

The experiment calculates the Born–Oppenheimer ground-state energy of the
helium hydride ion, **HeH+**, at fixed He–H separations. A local Qiskit VQE
estimate and a matched exact classical reference are plotted together. The
calculation is a **local ideal-state simulation**, not an IBM hardware result.

## What is included

```text
challenges/ibm-hehplus/
├── generate_submission.py       # Runs the real ten-point Qiskit calculation
├── hardware_prepare.py          # Opt-in IBM Runtime Estimator workflow
├── requirements-simulator.txt
├── requirements-hardware.txt
├── PRESENTATION_OUTLINE.md
└── artifacts/                   # Generated, reviewable submission outputs
    ├── hehplus_potential_energy_scan.json
    ├── hehplus_potential_energy_curve.csv
    ├── hehplus_potential_energy_curve.png
    ├── hehplus_potential_energy_curve.svg
    ├── hehplus_vqe_circuit_1.0A.png
    ├── hehplus_vqe_circuit_1.0A.txt
    ├── submission_manifest.json
    └── hardware/hehplus_hardware_preflight.json
```

`generate_submission.py` calls this challenge's own
[`backend/heh_plus.py`](backend/heh_plus.py); it does not import the parent
PepperQ backend, reimplement the molecular Hamiltonian, or introduce synthetic
energy data. The manifest hashes every generated scientific artifact.

## Standalone application

This folder is independently runnable. It contains a copied, isolated Python
quantum-chemistry backend and an isolated React + Vite + TypeScript dashboard.
Neither imports the PepperQ peptide frontend, peptide-analysis code, QAOA/QUBO
code, or parent backend at runtime.

```text
challenges/ibm-hehplus/
|- backend/                    # Independent Qiskit/PySCF calculation package
|  |- heh_plus.py             # Real VQE + matched exact-reference workflow
|  |- cli.py                  # Explicit calculation entry point
|  |- test_heh_plus.py        # Focused scientific tests
|  `- requirements.txt
|- frontend/                   # Independent React + Vite + TypeScript dashboard
|  |- package.json
|  |- vite.config.ts
|  `- src/
|- artifacts/                  # Versioned, verified precomputed results
|- generate_submission.py      # Explicitly regenerate local-simulator artifacts
`- hardware_prepare.py         # Explicit, opt-in hardware preparation only
```

The frontend is static by design: Vite copies the checked-in verified challenge
artifacts into its production build. It displays results immediately and never
triggers a VQE calculation on page load. The Python backend remains a separate,
explicit calculation tool.

## Reproduce the submission

Use Python 3.14.5 or a compatible Python environment for the verified local
simulator workflow.

```powershell
cd challenges/ibm-hehplus
python -m pip install -r requirements-simulator.txt
python -m pytest backend/test_heh_plus.py -q -p no:cacheprovider
python generate_submission.py
```

The generator runs every point on the fixed grid
`0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.5, 1.8, 2.0 Å`, then writes the JSON, CSV,
plot, optimized 1.0 Å Qiskit circuit diagram, portable text circuit, and
checksummed manifest under `artifacts/`. It is safe to rerun: it recalculates
the curve and replaces only challenge-owned exports.

To choose a different sampled grid or SLSQP stopping rule, make it explicit:

```powershell
cd challenges/ibm-hehplus
python generate_submission.py --distances 0.8 0.9 1.0 1.1 1.2 --maxiter 200 --ftol 1e-10
```

### Run the independent dashboard

The dashboard uses only the checked-in challenge artifacts. It has its own
package manifest and does not require the parent repository frontend or a live
Python server.

```powershell
cd challenges/ibm-hehplus/frontend
npm install
npm run dev
```

Create and verify the production build with:

```powershell
cd challenges/ibm-hehplus/frontend
npm run build
```

The application exposes an interactive total-energy curve and distance
selector, selected-point VQE/classical comparison and metadata, the verified
1.0 Å circuit image, choice rationale, reproducibility details, and a
simulation-versus-hardware section. The circuit image is always labeled as the
verified 1.0 Å run; it is never presented as a new circuit for another selected
distance.

The underlying focused tests cover the molecular particle sector, four-qubit
Jordan–Wigner mapping, real local VQE/reference agreement, and export shapes.

### Recorded software provenance

The generated scan JSON records package versions with every point. This
submission run used Python 3.14.5, Qiskit 2.6.2, Qiskit Algorithms 0.4.0,
Qiskit Nature 0.8.0, PySCF 2.15.0, NumPy 2.5.1, and SciPy 1.18.1. IBM Runtime
was intentionally not installed in this local simulator environment and no
hardware job was run. The optional hardware requirements pin
`qiskit-ibm-runtime==0.52.1`, whose client-side Estimator interface is used by
`hardware_prepare.py`.

## Molecular model and energy convention

| Item | Value |
| --- | --- |
| Molecule | HeH+ |
| Charge / electron count | +1 / 2 |
| Nuclear geometry | `He 0 0 0; H 0 0 R`, with `R` in Å |
| Electronic-structure driver | PySCF through Qiskit Nature `PySCFDriver` |
| Basis | STO-3G |
| Fermion-to-qubit mapping | `JordanWignerMapper`, no qubit reduction |
| Logical qubits | 4 |
| Reference / ansatz | Hartree–Fock reference + UCCSD |
| Variational parameters | 3 |
| VQE estimator / optimizer | `StatevectorEstimator` / SLSQP (`maxiter=200`, `ftol=1e-10`) |
| Classical reference | `NumPyMinimumEigensolver` exact diagonalization with Qiskit Nature’s physical-sector filter |
| Energy unit | Hartree |

The mapped qubit Hamiltonian is the **electronic** Hamiltonian. Each total in
the chart and data is formed as:

```text
E_total(R) = E_electronic(R) + E_nuclear_repulsion(R)
```

Nuclear repulsion is added exactly once. The VQE and exact reference use the
same HeH+, charge, two-electron sector, geometry, basis, and energy convention.

## Scientific choices

### Ansatz — Hartree–Fock + UCCSD

The Hartree–Fock initial state encodes the closed-shell `(1, 1)` alpha/beta
occupation for HeH+ in this model. UCCSD applies particle-conserving
single- and double-excitation operators from that physical reference, giving a
compact correlated state family for this small two-electron problem. It has
three variational parameters here and reaches the matched exact reference very
closely on the ideal-state simulator. The tradeoff is circuit cost: the
untranspiled UCCSD circuit is shallow at the abstraction level, but its
decomposed 1.0 Å circuit has depth 112 before a hardware-specific transpilation.
That depth is a reason to treat hardware results as a separate noisy
measurement experiment rather than as interchangeable with the statevector
result.

### Mapping — Jordan–Wigner

Jordan–Wigner maps each fermionic spin orbital to one qubit while using strings
of `Z` operators to preserve fermionic anticommutation. It is straightforward,
transparent, and directly supported by Qiskit Nature, which makes the mapping
easy to inspect and validate for this four-spin-orbital STO-3G problem. Its
cost is one qubit per spin orbital and, in general, parity strings that can
grow with orbital separation. We deliberately use no qubit reduction so the
four-qubit model and its particle sector remain explicit.

### Optimizer — SLSQP

SLSQP is a practical deterministic optimizer for this low-dimensional, smooth
ideal-state objective. Starting from the Hartree–Fock point, it gives an
inspectable convergence history and makes the local simulator experiment
reproducible. Finite-shot estimation, drift, and hardware noise can make its
objective noisy and its stopping behavior less reliable; it is not presented
as a hardware-robust optimizer.

### Basis — STO-3G

STO-3G is a minimal basis that keeps orbital, qubit, and circuit resources
small enough for a transparent hackathon-scale calculation. It is appropriate
for demonstrating the workflow, not for claiming basis-set-converged chemical
accuracy. The reported energies are only comparable within this stated model.

## Verified local-simulator curve

The checked source artifact was verified before creating this challenge area:
at 1.0 Å it reports VQE total energy
`-2.8602051225712977 Ha`, exact classical total energy
`-2.8602051225798046 Ha`, and absolute error
`8.5069729038878e-12 Ha`. The regenerated CSV is the authoritative table for
the artifacts in this directory; the ten-point values below document the
previously saved verified scan and serve as a transparent reproducibility
check.

| R (Å) | VQE total energy (Ha) | Exact total energy (Ha) | \|ΔE\| (Ha) |
| ---: | ---: | ---: | ---: |
| 0.7 | -2.830482959040519 | -2.8304829590638896 | 2.3371e-11 |
| 0.8 | -2.855708627223734 | -2.855708627228009 | 4.2748e-12 |
| 0.9 | -2.862617578795527 | -2.8626175787977766 | 2.2498e-12 |
| 1.0 | -2.8602051225712977 | -2.8602051225798046 | 8.5070e-12 |
| 1.1 | -2.853516188401112 | -2.853516188404373 | 3.2609e-12 |
| 1.2 | -2.845425337862080 | -2.8454253378627286 | 6.4837e-13 |
| 1.3 | -2.837496879670728 | -2.8374968796708897 | 1.6165e-13 |
| 1.5 | -2.8246826761864274 | -2.824682676189801 | 3.3737e-12 |
| 1.8 | -2.8139960345516704 | -2.8139960345553234 | 3.6531e-12 |
| 2.0 | -2.8107800991341914 | -2.8107800991343743 | 1.8296e-13 |

The lowest **sampled** point is 0.9 Å. That observation does not establish a
mathematically precise equilibrium geometry: this is a sparse fixed-nuclei scan
in a minimal basis, not a geometry optimization or an experimental
measurement.

## Optional IBM hardware workflow

No IBM hardware job has been submitted by this repository. The hardware script
is designed to make a later result auditable while protecting against accidental
cost.

First, generate a no-cost preflight record. It verifies the saved optimized
parameters against a rebuilt HeH+ Hamiltonian, but it does not authenticate,
transpile for a device, or submit anything:

```powershell
cd challenges/ibm-hehplus
python hardware_prepare.py
```

For a deliberate QPU run, use a Python version supported by the selected
`qiskit-ibm-runtime` release (Python 3.13 is the conservative choice for the
optional Runtime environment), configure IBM Quantum credentials outside this
repository, choose a backend, and then explicitly submit:

```powershell
cd challenges/ibm-hehplus
python -m pip install -r requirements-hardware.txt
python hardware_prepare.py --submit --backend YOUR_BACKEND --precision 0.02 --resilience-level 0 --wait
```

The script:

- rebuilds the actual HeH+ Jordan–Wigner electronic Hamiltonian and binds the
  locally optimized UCCSD parameters;
- transpiles that circuit with an IBM backend preset pass manager;
- applies `system.qubit_hamiltonian.apply_layout(isa_circuit.layout)` so the
  observable follows the physical-qubit layout;
- estimates the electronic expectation through IBM Runtime’s client-side
  Estimator, then adds nuclear repulsion exactly once;
- saves backend name, job ID, requested precision/shots and resilience setting,
  timestamps, physical layout, Runtime metadata, measured standard deviation,
  total energy, and errors against the local VQE and exact reference.

It will not choose a backend or submit without both `--submit` and `--backend`.
Uploading QASM to Composer alone does not evaluate the molecular Hamiltonian;
the Estimator observable measurement is the energy calculation. Current IBM
Runtime documentation describes the client-side Estimator and the
circuit/observable layout step, as well as precision/shot precedence:
[Estimator documentation](https://quantum.cloud.ibm.com/docs/en/api/qiskit-ibm-runtime/executor-estimator) and
[Estimator options](https://quantum.cloud.ibm.com/docs/en/ibm-quantum-compute/estimator-options).

## Limitations

- This is an electronic fixed-nuclei Born–Oppenheimer model, not a laboratory
  measurement or a complete rovibrational calculation.
- STO-3G and the active molecular model limit chemical accuracy.
- The local statevector estimator has neither shots nor hardware noise, so its
  near-exact VQE/reference agreement is not evidence of hardware performance
  or quantum advantage.
- The exact comparator is intentionally filtered to the physical two-electron
  sector; an unconstrained minimum over all Fock-space occupations would not be
  the molecular ground state requested here.
- Any future QPU result needs its own backend, calibration, shots/precision,
  mitigation, job ID, timestamp, and uncertainty record. It must not be
  retroactively labeled as this ideal-state result.
