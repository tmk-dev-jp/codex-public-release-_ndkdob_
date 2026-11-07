Repaired the Luna transport binding failure.

- `scripts/run_sycophancy_codex.py:147–150`: missing/mismatched final-file bindings now set `isError=true`, pausing dispatch.
- Tests cover mismatch, missing file and missing event; verify exactly one subprocess call, blocked continuation, preserved raw bytes and resumption at the next unused request.
- Correctly bound malformed model JSON remains `returned-invalid`.

**61 focused tests passed in 16.39s**; scoped Ruff and whitespace checks passed. No model calls. Source edits are finished and ready for freezing.
