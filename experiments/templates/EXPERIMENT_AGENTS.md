# Single experiment scope

- Read this record, its named config, `SCOPE.json`, and only exact scoped files.
- In DRAFT, list paths first; open only Python predeclared with a reason in budgeted `planning_reads`.
- In implementation, open `implementation_entry_reads` first; inspect one more scoped file only when current evidence requires it.
- Keep locked controls fixed; change only declared paths and symbols. Never edit `IMPLEMENTATION_DELTA.json` manually.
- Use aggregate metrics; never inspect checkpoints or histories by default.
- Finish the current phase and stop. Finalize this experiment before selecting another.
