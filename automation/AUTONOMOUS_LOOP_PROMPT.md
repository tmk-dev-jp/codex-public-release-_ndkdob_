Read `research/CONTEXT.md`, `research/STATE.json`, and `human/AUTONOMOUS_LOOP.ja.md`.
Run `python scripts/next_autonomous_step.py`.
If it returns `blocked`, report the substantive gate; recover presentation-only errors using `automation/PRESENTATION_REPAIR.md` before stopping.
If it returns `ready`, remember `operation` and use the listed phase skill.
Use scripts for state transitions, execution, monitoring, hashing, and context rebuilding.
After each phase, rebuild context and rerun the router.
Continue only while state, substantive evidence or gate action advances and the router returns `ready` with the same `operation`, for at most three phases. Routed novelty preparation counts as one phase.
Stop before an operation change, required human judgment, substantive failure, or no progress after correction. Unchanged observations or timestamps alone are not progress.
Never cross planning, implementation, execution, or result-review operations. End with the resulting state or one blocking error.
