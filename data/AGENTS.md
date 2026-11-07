# Data scope

- Treat `raw/` as immutable user-managed data and `processed/` as reproducible derivatives.
- Do not recursively inspect data directories or download data automatically.
- Read `MANIFEST.json` first and open only exact samples or metadata needed for the active experiment.
- Preserve split definitions and leakage controls during comparisons.
