# React + TypeScript + Vite

## Automatic molecular structure viewer

The Molecular Analysis page (`/chemistry`) automatically requests a generated
PDB model and displays it under Structure Stats with 3Dmol. No download or file
upload is required. It initially models `GAGA`; enter another 2–8-residue
standard sequence and click **Show structure** to update it. The modeled sequence
is independent of the page's demonstration candidate and descriptor fixtures.

Start the backend from the repository root in one terminal:

```powershell
python -m uvicorn backend.api:app --reload
```

Start the frontend from `frontend/` in another:

```powershell
npm ci
npm run dev
```

The adapter in `src/services/molecularStructure.ts` uses the existing FastAPI
0.2.0 `POST /optimize` contract and reads `best_structure_pdb`. Its default
backend URL is `http://127.0.0.1:8000`; set `VITE_STRUCTURE_API_BASE_URL` in
`.env.local` and restart Vite to change it. This URL is separate from the
proposed `/api/v1` APIs elsewhere in the UI. The backend allows localhost ports
5173 and 3000 by default; configure `PEPTIDE_CORS_ORIGINS` if using another origin.

Models use classical MMFF94 evaluation, seed 42, and up to three supported
backbone torsions with two angles each. The UI displays the actual modeled
sequence and provenance. These are generated conformers, not experimentally
verified structures, quantum electronic-structure results, or activity predictions.
If the backend is unavailable, the viewer displays an error and can be retried
using **Show structure**; it never substitutes a fabricated model. WebGL is
required. Local PDB/SDF/MOL loading remains available after a model is loaded.

This template provides a minimal setup to get React working in Vite with HMR and some Oxlint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the Oxlint configuration

If you are developing a production application, we recommend enabling type-aware lint rules by installing `oxlint-tsgolint` and editing `.oxlintrc.json`:

```json
{
  "$schema": "./node_modules/oxlint/configuration_schema.json",
  "plugins": ["react", "typescript", "oxc"],
  "options": {
    "typeAware": true
  },
  "rules": {
    "react/rules-of-hooks": "error",
    "react/only-export-components": ["warn", { "allowConstantExport": true }]
  }
}
```

See the [Oxlint rules documentation](https://oxc.rs/docs/guide/usage/linter/rules) for the full list of rules and categories.
