# Deterministic tooling scope

- Scripts are non-interactive, deterministic where practical, and silent during execution.
- Emit one `OK ...` line on success or one `ERROR ...` line to stderr on failure.
- State changes use declared transitions and atomic writes.
- Catch exceptions only in the outer CLI adapter. Do not hide failures, retry automatically, print traces, or create debug logs.
- Keep error artifacts compact: type, one-line message, experiment ID, and phase only.
- Update focused tests when state transitions, artifact schemas, or output contracts change.
