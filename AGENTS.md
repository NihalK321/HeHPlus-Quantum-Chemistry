# PepperQ: Repository Instructions for Codex and Coding Assistants

## 1. Mission and scope

**Project:** PepperQ (`peptide-project` repository)
**Event:** USC x IBM Qiskit Fall Fest 2026

PepperQ is a quantum-assisted molecular research prototype with two independent research modules:

1. **Quantum Optimization - Peptide Blend Research**: QAOA-based selection of whole peptide candidates for a research blend, informed by documented chemistry-derived objectives and compared with exact classical optimization for small instances.
2. **Quantum Chemistry - HeH+ Potential Energy Surface**: VQE-based electronic-structure studies of the helium hydride ion across multiple bond distances, compared with a classical reference within the same molecular model and basis.

These are scientifically distinct tasks. QAOA selects peptide candidates according to a mathematical objective; VQE estimates electronic-structure energies. A molecular visualization alone is not an electronic-structure calculation.

PepperQ is a research prototype, not medical advice. It must not claim clinical safety, therapeutic efficacy, proven peptide compatibility, synergy, binding, or laboratory validation without supporting evidence.

## 2. Module A - Quantum Optimization: peptide blend research

### Canonical workflow

1. A researcher specifies target pH, chemical-property goals, candidate pool, desired blend size, and justified research constraints.
2. Candidate generation imports or creates short peptide sequences and may explore position-specific substitutions. Do not imply an exhaustive sequence search unless one actually occurred.
3. Chemistry computes documented sequence descriptors with methods, units, source/version, conditions, and uncertainty.
4. Optional structural analysis may examine supplied or classically modeled conformers, atomic positions, steric contacts, or electrostatic descriptors for a limited candidate set. These remain hypotheses, not validated blend-interaction predictions.
5. QAOA selects a subset of whole peptide candidates using a chemistry-derived QUBO. One core binary variable means "select this peptide candidate," not "choose this amino acid at a sequence position."
6. The small problem is checked against exhaustive classical enumeration; report feasibility and objective score rather than unsupported quantum speedup.
7. Results expose selected sequences, component scores, pairwise terms, constraints, classical reference, provenance, and limitations.
8. Noise and error-mitigation studies are optional stretch work after the core workflow is verified.

### Minimum validated hackathon experiment

- Start with **8** small, chemically documented peptide candidates.
- Select exactly **3** candidates for a proposed research blend.
- There are **56** feasible three-of-eight subsets and **256** unconstrained bitstrings in an 8-qubit binary encoding.
- Use a stated normalization and documented scoring model; use pairwise penalties or proxies only when defensible.
- Produce the exact classical optimum by enumerating feasible subsets.
- Implement a real QAOA circuit with Qiskit and report observed optimization results.
- Compare QAOA and classical results under the same objective and constraints. Do not claim quantum advantage without rigorous evidence.
- Keep calculated, predicted, measured, simulated, and illustrative/demo values visibly separate.

### Preliminary blend objective

For peptide candidates indexed by `i`, let `x_i` mean inclusion in a blend. A proposed minimization form is:

`E(x) = -sum_i S_i x_i + gamma sum_(i<j) P_ij x_i x_j + lambda (sum_i x_i - k)^2`

- `S_i`: documented, normalized research-property score.
- `P_ij`: documented pairwise penalty or proxy; never assume it proves biological incompatibility.
- `k`: target blend size, initially 3.
- `gamma` and `lambda`: documented weights, checked for correct constraint enforcement.

The chemistry researcher and quantum developer must agree on the scoring contract and example before QUBO coefficients are finalized. Validate the direct chemical objective, QUBO coefficients, Ising mapping, sampled-bitstring interpretation, feasibility, and ranking.

## 3. Module B - Quantum Chemistry: HeH+ potential energy surface

### Research objective

Study the electronic ground-state energy of the helium hydride ion (`HeH+`) at multiple He-H bond distances using VQE and compare it with an appropriate classical reference **within the same molecular model and basis set**.

The frontend must clearly document and visualize, when supplied by verified backend outputs:

- molecule identity: `HeH+`;
- molecular charge: `+1`;
- electron count: `2`;
- bond distance in angstroms;
- VQE and classical-reference energies in Hartrees;
- energy convention: electronic energy or total molecular energy, with nuclear repulsion treatment explicit;
- basis set;
- fermion-to-qubit mapping;
- ansatz;
- classical optimizer;
- qubit count, parameter count, circuit depth, iteration count, convergence, and circuit metadata;
- calculation status, provenance, uncertainty, limitations, and relevant execution context.

### Scientific requirements

- Use an actual VQE workflow in Qiskit or a compatible quantum-chemistry stack; React must not perform or pretend to perform the calculation.
- Keep the Hamiltonian, molecular charge, electron count, basis, unit system, and energy convention consistent across all points in a potential-energy curve.
- Generate the curve only from verified outputs. Never invent molecular energies, convergence traces, minimum-energy geometries, or error values.
- A 2D or 3D molecular structure diagram may show valid atomic coordinates, but it is not itself an electronic-structure result.
- Explain why the selected ansatz, mapping, optimizer, and basis are appropriate using actual calculation metadata. If a choice is unknown, display **Not yet specified**.
- Compare VQE against a classical reference computed in the same model and basis. Report error only where mathematically meaningful.
- Do not conflate this module with peptide QAOA, peptide descriptors, or the peptide compatibility proxy.

## 4. Technology and frontend architecture

- **Frontend:** React, TypeScript, Vite, Tailwind CSS.
- **Scientific UI:** Recharts for compact summary charts; Plotly for lazy-loaded interactive scientific plots; 3Dmol.js only for valid supplied molecular structures.
- **Backend:** Python and FastAPI.
- **Quantum:** IBM Qiskit, Qiskit Aer, QAOA, VQE, and verified classical reference routines.
- **Chemistry:** documented peptide descriptors, trustworthy datasets, and appropriately scoped classical molecular-modeling tools.

Keep API adapters isolated under `frontend/src/services/`. Before frontend code consumes a new endpoint, agree with the backend teammate on a versioned request/response shape. Do not silently change shared schemas or backend public interfaces.

Frontend data models must preserve explicit provenance such as `demo`, `calculated`, `simulated`, `hardware`, or `unavailable`. Demo values must never be labeled as chemistry calculations, Qiskit results, or classical references.

## 5. Expected project organization

Relevant working areas normally include:

```text
peptide-project/
|-- frontend/
|   `-- src/
|       |-- components/
|       |-- features/
|       |-- services/
|       `-- types/
|-- backend/
|-- experiments/
|-- data/
|-- research/
|-- tests/
`-- AGENTS.md
```

This is an architectural guide, not proof that every file exists. Do not create, move, or restructure files merely to match this illustration.

## 6. Team ownership and collaboration

There are three teammates working concurrently.

### Frontend developer and integration lead

Owns `frontend/`, `backend/api.py`, and explicitly approved integration code.

Responsibilities include React/TypeScript UX, all research views, scientific visualization, frontend API integration, and final demo preparation.

May edit `frontend/` and approved API integration files, including agreed changes to `backend/api.py`. Shared schemas and API contracts still require coordination with the backend developer before they change.

### Quantum/backend teammate

Owns their assigned backend optimization, quantum, benchmark, VQE, experiment, and related test files. This normally includes `backend/optimizer.py`, `backend/quantum.py`, `backend/benchmark.py`, `experiments/`, and agreed optimization or quantum-chemistry tests.

Responsibilities include QUBO construction, QAOA, exact enumeration, VQE/electronic-structure workflows, mappings, ansatz/optimizer choices, classical references, noise studies, and validation.

May edit the files explicitly assigned to that role. They do not need frontend approval to work in their owned backend or experiment files.

### Chemistry/peptide teammate

Owns `research/`, `data/`, source references, chemical scoring specifications, and research methodology. `backend/chemistry.py` requires coordination with the backend teammate.

Responsibilities include candidate sourcing, amino-acid properties, substitutions and positioning, charge/hydropathy conventions, chemical objectives, data limitations, and optional structural-model methodology.

May edit `research/`, `data/`, and their assigned chemistry code. They do not need frontend approval to work in their owned research, data, or chemistry files.

Shared files such as backend schemas, `backend/chemistry.py`, root configuration, README, and integration tests require explicit agreement before editing. Protect teammates' files and all uncommitted changes; do not overwrite, delete, rename, reformat, or clean up another person's work incidentally.

## 7. Branch, ownership, and collaboration rules

### Feature-branch policy

- Every teammate works on their own assigned feature branch. Nobody edits directly on `main`.
- The frontend developer works on `feature/frontend-integration`.
- The quantum/backend developer works on their own assigned backend feature branch.
- The chemistry developer works on their own assigned chemistry feature branch.
- Never require a backend or chemistry developer to work on `feature/frontend-integration`, and never require the frontend developer to work on another teammate's branch.
- Do not switch branches automatically. If the current branch is not the developer's assigned feature branch, stop and ask for direction.

Before every edit:

1. Inspect Git status, current branch, repository structure, and applicable instructions.
2. Confirm work is on the current developer's assigned feature branch, never `main`.
3. Check ownership and preserve any teammate changes or uncommitted work.
4. For work beyond the current approved scope, state proposed files and obtain approval.

Always:

- Work only in paths approved for the current task and role. Developers may edit the files they explicitly own.
- Do not modify a teammate's owned files without that teammate's approval. Shared interfaces and files require coordination.
- Never overwrite, delete, rename, reformat, or clean up another teammate's files or uncommitted work incidentally.
- Do not switch branches, merge, rebase, reset, clean, force-push, or discard changes automatically.
- Do not commit, push, create pull requests, or merge automatically or without explicit instruction.
- Do not use `git add .` indiscriminately.
- Avoid broad dependency upgrades or lockfile churn without approval.
- Never expose IBM credentials, tokens, CRNs, local `.env` files, node_modules, or virtual environments.
- Keep `.env.example` placeholder-only.

At the start of a new session, read this file, inspect the repository read-only, report branch/status and relevant existing code, then propose the smallest next change unless the user has already authorized edits.

## 8. Scientific communication standards

- Distinguish measured laboratory properties, published data, calculated descriptors, predicted structures, simulator results, hardware results, and illustrative UI fixtures.
- State units, relevant conditions, methods, source/version, uncertainty, and limitations where applicable.
- Charge complementarity, sequence similarity, hydropathy, or a plausible conformer do not prove compatibility, affinity, synergy, aggregation resistance, solubility, or safety.
- For QAOA, compare against exact classical enumeration for the small peptide-blend problem.
- For VQE, state the molecule, charge, electron count, basis, mapping, ansatz, optimizer, energy convention, and reference method before comparing energies.
- For noise experiments, report shot counts, seeds, noise assumptions, statistical uncertainty, mitigation overhead, and possible degradation.

## 9. Definition of done

Prioritize work in this order:

1. Agree peptide chemistry scoring and candidate data.
2. Verify peptide classical baseline and QUBO.
3. Produce real local QAOA results.
4. Agree and implement frontend API contracts.
5. Produce verified HeH+ VQE and classical-reference outputs with a documented methodology.
6. Display reproducible, provenance-rich results and comparisons.
7. Add limited structural analysis, hardware work, and error mitigation only when justified.

For every authorized coding task:

1. State intended files and scope.
2. Make minimal localized changes.
3. Run focused tests/builds.
4. Report changed paths, verification, known limits, and the next safe step.

**Success:** a defensible research demonstration with a reproducible peptide-blend QAOA workflow and a separate, scientifically documented HeH+ VQE potential-energy study - not an expansive demo with fabricated results.
