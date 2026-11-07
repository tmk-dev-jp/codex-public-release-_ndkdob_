Luna delta complete; **59 focused tests passed in 14.22s**, scoped Ruff and whitespace checks passed.

Changed:

- `scripts/sycophancy_study.py`: strict `qwen38` and `luna-max` profiles; freezes/verifies bridge source, executable, transport and settings.
- `scripts/run_sycophancy_codex.py`: sequential CLI transport, fixed wrapper, no retries/fallback; preserves exact streams, final output, exit status and thread metadata.
- Both corresponding test modules: fake-process success, invalid outputs, tools, failures, pause/resume and overwrite protection.

After delta review:

```bash
python scripts/sycophancy_study.py prepare \
  --runtime luna-max \
  --run-dir review/sycophancy/<new-luna-run>

python scripts/run_sycophancy_codex.py \
  --run-dir review/sycophancy/<new-luna-run> \
  --availability-confirmed
```

The transport uses the approved custom provider configuration and a frozen **900-second timeout per attempt**. It allows only an optional final-file terminating LF when checking against the exact last agent-message event.

No real inference, credential reads, or existing study-artifact edits. Actual connectivity and human semantic review remain pending.
