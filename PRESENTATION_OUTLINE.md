# Five-minute judge presentation — HeH+ potential-energy curve

## 1. Challenge and result (0:00–0:35)

- The task is the one-dimensional Born–Oppenheimer potential-energy curve of
  the helium hydride ion, HeH+, as a function of the He–H separation.
- We calculated ten fixed geometries from 0.7 to 2.0 Å with Qiskit VQE and a
  matched exact classical reference.
- Lead with `artifacts/hehplus_potential_energy_curve.png`: the curves overlap
  on this ideal-state simulation. This is a validation result, not a claim of
  quantum advantage or physical-hardware accuracy.

## 2. Molecular Hamiltonian and comparison contract (0:35–1:15)

- State the molecular model up front: HeH+, charge +1, two electrons,
  closed-shell spin 0, PySCF/Qiskit Nature, STO-3G.
- At each fixed nuclear separation, map the electronic Hamiltonian to qubits.
- Define the plotted quantity precisely:
  `E_total = E_electronic + E_nuclear_repulsion`, with nuclear repulsion added
  exactly once to both VQE and reference totals.
- The classical reference is exact diagonalization in the same model and the
  physical two-electron sector—not an unrelated literature value.

## 3. Quantum workflow (1:15–2:00)

- Show `artifacts/hehplus_vqe_circuit_1.0A.png` and identify four logical
  qubits and three variational parameters.
- Start from the Hartree–Fock occupation, construct UCCSD, use the
  Jordan–Wigner mapped electronic Hamiltonian, and optimize with SLSQP through
  `StatevectorEstimator`.
- For each distance: optimize VQE, exact-diagonalize the same Hamiltonian, add
  nuclear repulsion, then export every value and metadata to JSON/CSV.

## 4. Why these choices (2:00–3:05)

- **Hartree–Fock + UCCSD:** a physically meaningful closed-shell reference;
  singles and doubles capture correlation for this small two-electron model.
  Tradeoff: decomposed circuit depth is 112 at 1.0 Å before hardware mapping.
- **Jordan–Wigner:** transparent direct fermion-to-qubit mapping that preserves
  anticommutation and makes the four-spin-orbital model easy to validate.
  Tradeoff: one qubit per spin orbital and parity-string overhead.
- **SLSQP:** suitable for three smooth parameters on an exact-state simulator;
  finite-shot hardware objectives may make it unreliable.
- **STO-3G:** deliberately small and tractable; not basis-set-converged
  chemical accuracy.

## 5. Actual numerical evidence (3:05–4:05)

- At 1.0 Å: VQE total `-2.8602051225712977 Ha`; exact classical total
  `-2.8602051225798046 Ha`; absolute error `8.5069729038878e-12 Ha` in the
  verified saved scan.
- Point judges to `artifacts/hehplus_potential_energy_curve.csv` and
  `artifacts/hehplus_potential_energy_scan.json` for all ten calculations,
  convergence histories, optimal parameters, circuit metadata, and package
  versions.
- Mark 0.9 Å as the lowest **sampled** energy, not as a precise equilibrium
  geometry.

## 6. Limitations and hardware readiness (4:05–5:00)

- Local statevector VQE has no shot noise or device noise; its agreement with
  exact diagonalization validates the implementation under the selected model.
- A sparse STO-3G scan cannot make experimental, basis-set-convergence, or
  exact-equilibrium claims.
- `hardware_prepare.py` is an opt-in next step: it binds the optimized circuit,
  transpiles it, maps the observable with the physical layout, measures with
  IBM Runtime Estimator, adds nuclear repulsion once, and saves job provenance
  and measured errors.
- Be explicit: no hardware result is claimed unless a completed job ID and
  hardware record exist.
