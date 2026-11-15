# HeH+ challenge frontend

This is an independent React + Vite + TypeScript presentation of the verified
static artifacts in `../artifacts`. It does not import the main PepperQ
frontend and it does not run quantum chemistry in the browser.

## Run locally

```powershell
cd challenges/ibm-hehplus/frontend
npm install
npm run dev
```

Run `npm run build` to produce a self-contained static site in `dist/`. Vite's
`publicDir` is deliberately configured as `../artifacts`, so the build copies
the checked-in scan JSON, CSV/SVG curve, circuit assets, submission manifest,
and hardware preflight record alongside the frontend bundle.

The interface loads only:

- `hehplus_potential_energy_scan.json`
- `hardware/hehplus_hardware_preflight.json`
- the verified chart, circuit, CSV, SVG, and manifest linked from the page

The hardware card reads the preflight record. It must continue to say that no
hardware result exists unless a completed, auditable hardware record replaces
that static artifact.
