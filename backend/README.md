# Independent HeH+ VQE backend

This folder is the self-contained calculation backend for the IBM Qiskit Fall
Fest HeH+ challenge.  It does not import `backend/quantum_chemistry` or any
other application module from the parent repository.

## Reproduce

From the repository root, install the local simulator dependencies:

```powershell
python -m pip install -r challenges/ibm-hehplus/backend/requirements.txt
```

Run one actual local VQE point (default 1.0 Angstrom):

```powershell
python challenges/ibm-hehplus/backend/cli.py --distance 1.0 --output-directory challenges/ibm-hehplus/backend/.local
```

Run a fresh potential-energy scan using the same molecular model at every
distance:

```powershell
python challenges/ibm-hehplus/backend/cli.py --scan 0.7 0.8 0.9 1.0 1.1 1.2 1.3 1.5 1.8 2.0 --output-directory challenges/ibm-hehplus/backend/.local
```

Alternatively, change into `challenges/ibm-hehplus` and use the package entry
point:

```powershell
python -m backend --scan 0.9 1.0 --output-directory backend/.local
```

The CLI writes a provenance-rich JSON document, and a single-point run also
writes Qiskit's portable text circuit drawing.  Outputs under `.local/` are
ignored because they are reproducible calculation artifacts with timestamps.

Run focused verification tests without touching project-wide tests:

```powershell
python -m pytest challenges/ibm-hehplus/backend/test_heh_plus.py -q -p no:cacheprovider
```

## Fixed model

- Molecule: HeH+, charge `+1`, two electrons, spin `0` (`(1, 1)` alpha/beta).
- Geometry: `He 0 0 0; H 0 0 R`, passed to PySCF in Angstrom.
- Basis: STO-3G restricted-HF integrals through Qiskit Nature `PySCFDriver`.
- Mapping: `JordanWignerMapper`, no qubit reduction (four qubits).
- Reference and ansatz: `HartreeFock` plus particle-conserving `UCCSD`.
- VQE: `StatevectorEstimator` with SLSQP (`maxiter=200`, `ftol=1e-10`).
- Classical comparator: `NumPyMinimumEigensolver` behind Qiskit Nature's
  physical-sector-filtered `GroundStateEigensolver`.

The mapped qubit Hamiltonian yields electronic energy.  The backend records
PySCF nuclear repulsion separately and reports total molecular energy as
`E_electronic + E_nuclear_repulsion`, exactly once, in Hartree.  It is a local
ideal-state calculation, not an IBM hardware run or a chemical-accuracy claim.
