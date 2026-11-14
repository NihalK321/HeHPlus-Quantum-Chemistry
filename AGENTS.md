# PepperQ — Repository Instructions for Codex and Coding Assistants

## 1. Mission and scientific scope

**Project:** PepperQ (`peptide-project` repository)

**Event:** USC × IBM Qiskit Fall Fest 2026

**Primary focus:** Quantum optimization applied to peptide chemistry and research-oriented peptide-blend selection.

**Secondary focus:** Quantum noise and error mitigation, only after the core workflow works.

PepperQ helps **laboratory researchers** explore short peptide sequences and prioritize **combinations of peptide candidates** for further study. A researcher defines chemical targets and experimental constraints; the application analyzes a manageable candidate pool, builds a chemically motivated optimization objective, and uses QAOA (via IBM Qiskit) to select candidate blends. It compares results with exact classical optimization for small instances.

This is a **research prototype**, not an application that recommends peptides for personal use or claims clinical safety, therapeutic efficacy, proven synergy, or laboratory-confirmed blend compatibility.

**Central research question:** Can sequence substitutions, peptide descriptors, and cautiously modeled structural or pairwise information help formulate a meaningful quantum optimization problem for selecting peptide research blends?

## 2. Canonical workflow

1. **Research inputs:** Researcher specifies target pH, chemical property goals, candidate pool, desired blend size, and any justified experimental constraints.
2. **Candidate generation:** Generate or import short peptide sequences; permit position-specific amino-acid substitutions. Never imply all possible sequences were searched unless they actually were.
3. **Chemistry:** Calculate sequence-derived properties with documented methods and units (e.g., molecular mass, estimated charge at specified pH, hydropathy using a named scale); track sources and uncertainty.
4. **Optional structural analysis:** For a limited candidate subset, examine approximate conformers, atomic positions, steric contacts, or electrostatic descriptors **using suitable classical modeling tools** and clearly state assumptions. These are hypotheses, not validated blend interaction predictions.
5. **Optimization:** Select a subset of entire peptide **candidates** using a chemistry-derived QUBO and QAOA. In the core blend model, one binary variable represents whether a peptide is selected, **not** which amino acid occupies a position.
6. **Verification:** Compare results to exhaustive classical enumeration for small problems; report feasibility and objective score, not unsupported quantum speedup.
7. **Results:** Show selected sequences, component scores, pairwise terms, constraints, reference solution, and limitations in the research interface.
8. **Optional noise study:** Investigate noisy simulations and error mitigation once items 1–7 are working and tested.

**Important distinction:** Sequence design/substitution creates or filters candidates; **blend selection** is the primary QAOA task. QAOA is not itself an atomic simulation engine or a quantum chemistry calculation.

## 3. Minimum validated hackathon experiment

- Begin with **8** small, chemically documented peptide candidates.
- Select exactly **3** candidates for a proposed research blend.
- There are **56 feasible** three-of-eight selections; an unconstrained 8-qubit binary encoding has **256** bitstrings.
- Use a stated scoring model, normalization, and (only where defensible) pairwise penalties.
- Produce the **exact classical optimum** by enumerating all feasible subsets.
- Implement a real **QAOA** circuit with Qiskit and show its observed optimization results.
- Display the classical comparison and explain possible QAOA shortcomings.
- Keep actual calculations separate from mock/demo data; never present placeholders as measured results.

Do not block the working MVP on 3D prediction, all 20 amino acids at every position, a large search space, real hardware, or error mitigation.

### Initial mathematical model (subject to chemistry review)

For peptide candidates indexed by `i`, let `x_i ∈ {0,1}` indicate inclusion in a blend. A preliminary minimization objective is:

`E(x) = -Σ_i S_i x_i + γ Σ_{i<j} P_ij x_i x_j + λ (Σ_i x_i - k)^2`

- `S_i`: documented, normalized research-property score.
- `P_ij`: documented pairwise **penalty or proxy**, **not assumed biological incompatibility**.
- `k`: target number of peptides (initially 3).
- `γ, λ`: documented weights, with penalty strength checked for constraint enforcement.

The chemistry researcher and quantum developer must **agree on the scoring contract and example** before finalizing QUBO coefficients. Any extra constraints need an explicit correct formulation and test. Benchmark the QUBO objective against a direct implementation of the chemical scoring rules.

## 4. Team roles and file ownership

There are **three teammates** working concurrently in one GitHub repository.

### Project lead — frontend and integration (repository owner using this assistant)

**Owns:** `frontend/`, `backend/api.py`, and frontend integration code that has been explicitly assigned.

Tasks: React/TypeScript application, Research Dashboard, Peptide Designer, optimization settings, Peptide Results Explorer, Trade-Off Explorer, chemistry displays, quantum-vs-classical comparison, experiment visualization, API integration, and final demo.

### Quantum/backend teammate

**Owns:** `backend/optimizer.py`, `backend/quantum.py`, `backend/benchmark.py`, `experiments/`, plus any agreed optimization tests.

Tasks: QUBO construction, QUBO-to-Ising conversion, QAOA, exact enumeration, score and feasibility validation, noise experiments, optional error mitigation.

### Chemistry/peptide teammate

**Owns:** `research/`, `data/`, source references, and chemical scoring specifications. Implemented chemistry code in `backend/chemistry.py` requires coordination with the backend teammate.

Tasks: candidate sourcing, amino acid property data, substitutions and sequence positioning, charge and hydropathy conventions, documented chemistry objectives, scientific limitations, and optional structural-model methodology.

**Shared files** such as `backend/schemas.py`, `backend/chemistry.py`, root configuration files, `README.md`, and integration tests require agreement before editing. Existing repository contents take precedence over this proposed ownership scheme until the team confirms responsibilities.

## 5. Expected project organization (not proof these files exist)

```text
peptide-project/
├── frontend/
│   ├── src/components/
│   ├── src/pages/
│   ├── src/services/api.ts
│   └── src/types/
├── backend/
│   ├── api.py
│   ├── schemas.py
│   ├── chemistry.py
│   ├── optimizer.py
│   ├── quantum.py
│   └── benchmark.py
├── experiments/
├── data/
├── research/
├── tests/
├── docs/
├── AGENTS.md
├── .gitignore
├── requirements.txt
└── README.md
```

Do **not** create all files by default, overwrite working code, or restructure the repository just to match this illustration. Inspect first.

## 6. Planned product features

1. **Research Dashboard** — overview of experiments and results.
2. **Peptide Designer** — chemical targets, candidate selection, substitutions, and positional variants.
3. **Quantum Optimization Engine** — chemistry-derived QUBO + QAOA blend selection.
4. **Molecular Chemistry Analyzer** — sequence descriptors; limited clearly labeled structural modeling when available.
5. **Quantum vs. Classical Comparison** — objective value, optimality gap, constraint satisfaction, and measured run metadata.
6. **Peptide Results Explorer** — ranked blends with transparent score breakdowns.
7. **Optimization Trade-Off Explorer** — how changing research objectives affects selected blends.
8. **Quantum Noise & Error Mitigation Lab** — optional, measured experiment, not a prerequisite for the MVP.

The frontend may use **clearly labeled mock data** while integration is incomplete. Never label mock data as computed Qiskit results or verified chemistry.

## 7. Technical stack and API coordination

- **Frontend:** React, TypeScript, Vite, Tailwind CSS; chart library as warranted by existing code.
- **Backend:** Python and FastAPI.
- **Quantum:** IBM Qiskit, Qiskit Aer, QAOA and classical optimization routines.
- **Chemistry:** documented peptide descriptors, trustworthy datasets, and optional appropriately scoped classical molecular modeling tools.
- **Collaboration:** GitHub, feature branches, reviewed pull requests.

**Before independently building API-consuming code**, agree with the backend teammate on a versioned request/response shape (candidate IDs, sequences, descriptors and units, selection count, weights, selected IDs, method, scores, constraints, runtime metadata, errors, and explicit `mock`/`simulated`/`hardware` provenance). Keep API adapters isolated under `frontend/src/services/`. Do not silently change shared schemas.

## 8. Strict rules to protect teammates' code

**Before any edit:**

1. Inspect `git status`, the current branch, repository structure, and applicable instructions.
2. Confirm work is on the project lead's **feature branch** (for example, `feature/frontend-integration`), **not `main`**.
3. Check whether targeted files are owned by someone else or already modified.
4. For work beyond the approved scope, first explain proposed files and request approval.

**Always:**

- Work only in the files explicitly assigned or approved for the current task.
- Preserve teammates' commits, uncommitted work, and public interfaces.
- Never overwrite, delete, rename, reformat, or "clean up" other people's files incidentally.
- Do not silently switch branches, merge, rebase, or resolve conflicts by discarding work.
- Do not run destructive Git operations (including `reset --hard`, `clean -fd`, forced push, or checkout/restore that discards changes).
- Do not commit, push, create pull requests, or merge without the user's explicit instruction.
- Do not use `git add .` indiscriminately; stage only approved paths.
- Avoid broad dependency upgrades or lockfile churn without approval.
- Run focused builds/tests before declaring a change complete, and report what was actually verified.
- Never place IBM API keys, CRNs where inappropriate, tokens, `.env`, credentials, `node_modules`, or virtual environment files into commits. Keep `.env.example` placeholder-only.

**Codex first task in a new session:** Read this file, inspect the repository **read-only**, report branch/status and existing code, propose the smallest next change within the current user's scope, and wait for approval unless the user has already authorized specific edits.

## 9. Scientific accuracy and validation

- Distinguish measured laboratory properties, published data, calculated sequence descriptors, predicted structural values, and illustrative scores.
- Always specify units, relevant conditions (e.g., pH, temperature), hydropathy scales, molecular mass conventions, data source, and uncertainty when appropriate.
- A plausible 3D conformer is **not** a validated fold, peptide-peptide docking solution, or stable formulation.
- Charge complementarity, sequence similarity, and hydrophobicity are **not by themselves proof** of peptide compatibility, binding affinity, synergy, aggregation resistance, or solubility.
- Don't invent pairwise interaction data to make the optimizer look impressive. If illustrative proxies are required, mark them clearly and do not imply real-world validity.
- Validate the direct chemical objective, quadratic QUBO coefficients, Ising mapping, sampled bitstring interpretation, feasibility, and rankings.
- For the small problem, use exact classical enumeration as ground truth and compare QAOA against it. Do not claim quantum advantage without rigorous evidence.
- For noise experiments, report shot counts, random seeds, noise assumptions, statistical uncertainty, and mitigation overhead. Mitigation may make performance worse.
- This platform prioritizes **research candidates**, not medical treatment decisions.

## 10. Workflow and definition of done

Prioritize in this order:

1. Chemistry scoring specification and candidate dataset agreed upon across the team.
2. Exact classical baseline and verified QUBO.
3. Working local QAOA results from real Qiskit execution.
4. API contract and integrated frontend displaying real outputs.
5. Clear result explanations and reproducible benchmark visuals.
6. Limited substitution/3D structural analysis only if valid and affordable.
7. Error mitigation / IBM hardware only as a stretch goal.

For each authorized coding task:

1. State the intended files and scope.
2. Make minimal, localized changes.
3. Execute the relevant tests/builds where possible.
4. Summarize **changed paths**, **what was verified**, **what remains unverified**, and **the next safe step**.

**Success for the hackathon:** A working, reproducible, chemically motivated peptide-blend QAOA optimizer that researchers can understand and that the team can defend scientifically—rather than an expansive but unvalidated product demo.
