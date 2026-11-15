# Additive peptide catalog

`data/pepperq_extras.sqlite` is a local, additive catalog. It is deliberately
ignored by Git: it must not replace, migrate, or modify the original
`backend/peptide_library/.local/pepperq_peptides.sqlite3` database.

The catalog importer retains source records separately. Its current 5,001-row
snapshot contains repeated sequences, so row counts are not candidate counts.
The merged PepperQ endpoint performs exact normalized-sequence deduplication
and retains source provenance for every matching record.

## Recreate a local catalog

Run these commands from the repository root. They query live public APIs, so a
fresh import is reproducible as a procedure but is not guaranteed to be byte
identical to another day's snapshot.

```powershell
python backend/peptide_library/extra_catalog.py --db data/pepperq_extras.sqlite import-uniprot --limit 5000
python backend/peptide_library/extra_catalog.py --db data/pepperq_extras.sqlite import-retatrutide
python backend/peptide_library/extra_catalog.py --db data/pepperq_extras.sqlite stats
Get-FileHash data/pepperq_extras.sqlite -Algorithm SHA256
```

The retatrutide record is sourced from its PubChem CID and ChEMBL identifier.
It is intentionally sequence-less and marked as a chemically modified peptide;
it must not be sent to sequence-only chemistry scoring or a sequence-based QAOA
candidate pool until its modifications are explicitly supported.

The supplied local snapshot was observed with SHA-256
`F4B9EC11D5D9A0E38332DCE4AFB27D344EAF0E9D402F8DE7F8D2CC2A2A1AF17E`.
Use the hash to confirm a teammate received the same snapshot; do not expect a
fresh live import to reproduce it byte-for-byte.

## API surfaces

- `/api/peptide-extras` exposes the unmodified additive catalog router.
- `/api/v1/peptide-catalog` is the read-only, deduplicated catalog used by the
  Designer. It preserves source references and does not add the original and
  additive row totals together.
