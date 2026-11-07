# Data policy

- `raw/` contains immutable user-managed source data.
- `processed/` contains reproducible derived data.
- Codex must not recursively inspect either directory.
- Store only compact shape, count, split, license, leakage, and hash information in `MANIFEST.json`.
- Never download data automatically from model, data-loader, or training code.
