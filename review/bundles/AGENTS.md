# Review bundle scope

- Treat each child directory as a closed read-only evidence bundle.
- Read only the bundle's named Markdown/JSON files and exact files under `implementation/`.
- Do not browse outside the bundle.
- For plan review, read only `PLAN_AUDIT_REQUEST.json`; test goal alignment, metric gaming, evaluation separation, baseline comparability, intervention clarity, and profile fit.
- For implementation review, treat `IMPLEMENTATION_DELTA.json` hashes and changed symbols as machine facts; judge plan fidelity, invariants, leakage, optimization, metrics, reproducibility, and scope.
- For integrity review, check provenance, plan adherence, metric validity, leakage risk, and scope discipline before claims are evaluated.
- Judge the locked decision rule; separate support, contradiction, limitations, and unresolved uncertainty.
- Do not revise success criteria, edit code, inspect checkpoints, or start another experiment.
- Return only the requested concise plan, implementation, integrity, or evaluation body in English.
