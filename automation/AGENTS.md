# Automation scope

- By default, execute one bounded workflow operation from `research/STATE.json`.
- Continue for at most three phases only while `next_autonomous_step.py` returns the same `operation`.
- Never cross planning, implementation, execution, or result-review operations in one turn.
- A current request for `$run-one-unattended-loop` or `$run-one-agent-led-loop` may span one target. Only the latter delegates human scientific decisions; never infer either from normal automation.
- Do not start a new experiment while another is active.
- Use at most one subagent per phase; never create a reviewer panel or automatic retry.
- Surface one final success or error result only.
