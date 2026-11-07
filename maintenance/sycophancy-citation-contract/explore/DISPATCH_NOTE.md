# Actual exploration profile

The reused gate template recorded `agent_type=default` in the exploration request.
The actual dispatch used the read-only `explorer` role for the specific codebase
question, with `gpt-6-astra` and reasoning `high`. The original request is retained
unchanged. The exploration report made no edits. The implementation and both audit
dispatches used their locked `default/gpt-6-astra/high` profiles exactly.
