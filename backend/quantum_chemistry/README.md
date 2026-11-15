# HeH+ VQE experiment

This isolated package implements PepperQ's quantum-chemistry module. It is not
part of the peptide QAOA implementation: it calculates the fixed-geometry
electronic structure of the helium hydride ion, `HeH+`.

## Method

- **Molecule:** `HeH+`, charge `+1`, two electrons, PySCF spin `0` (the
  closed-shell `(1, 1)` alpha/beta sector).
- **Initial geometry:** `He 0 0 0; H 0 0 1.0`, with the coordinate explicitly
  passed to PySCF as Angstrom.
- **Model chemistry:** PySCF restricted-HF integrals in `STO-3G`.
- **Qubit Hamiltonian:** Qiskit Nature `JordanWignerMapper`, with no qubit
  reduction.
- **Ansatz:** Qiskit Nature `UCCSD` with a `HartreeFock` initial state.
- **VQE:** Qiskit `StatevectorEstimator` and `SLSQP`. This is an exact-state
  local simulator, not a hardware or noise simulation.
- **Classical reference:** Qiskit Algorithms `NumPyMinimumEigensolver`, wrapped
  by Qiskit Nature's `GroundStateEigensolver` and constrained with
  `problem.get_default_filter_criterion()` so exact diagonalization uses the
  physical two-electron sector.

The mapped Hamiltonian reports **electronic energy**. This package reports the
PySCF/Qiskit Nature nuclear repulsion separately and calculates **total
molecular energy** as:

```text
E_total = E_electronic + E_nuclear_repulsion
```

All energies are in Hartree. Results are model-specific calculated values, not
experimental molecular energies or evidence of quantum advantage.

## Reproduce

From the repository root, install the package-local dependencies if they are
not already available:

```powershell
python -m pip install -r backend/quantum_chemistry/requirements.txt
```

Run the requested first point at 1.0 Angstrom:

```powershell
python -m backend.quantum_chemistry --distance 1.0
```

Run a small potential-energy scan using the same model at every point:

```powershell
python -m backend.quantum_chemistry --scan 0.8 1.0 1.2
```

The commands write JSON provenance/results and Qiskit text circuit drawings to
`backend/quantum_chemistry/.local/`, which is deliberately ignored by Git.
The JSON contains version information, geometry, energy conventions,
convergence history, UCCSD/SLSQP settings, circuit depth, qubit/parameter
counts, and the exact-reference comparison.

## Test

```powershell
python -m pytest backend/quantum_chemistry/test_heh_plus.py -q
```

Tests skip cleanly when the optional quantum-chemistry stack is absent. When it
is installed, they run an actual small local VQE calculation and only assert
relationships that follow from the stated model.
