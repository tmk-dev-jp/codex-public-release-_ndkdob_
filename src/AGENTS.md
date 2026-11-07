# Implementation scope

- Use `$implement-experiment` only after the plan is locked; edit only exact paths in `SCOPE.json`.
- Preserve the hypothesis, baseline, metric, threshold, data split, checkpoint rule, and budget.
- Prefer direct code over new abstractions until reuse is demonstrated.
- Validate only research-critical contracts: configuration, shapes, non-empty splits, finite loss or gradients, metric compatibility, and locked artifacts.
- Let library exceptions propagate. Catch once at a CLI boundary; do not add automatic retries, silent fallbacks, broad exception hierarchies, permanent debug code, or verbose diagnostics.
- Implement the coherent method and its declared comparison arms, add focused tests, and run at most `dl-sanity` here.
- Do not add console progress, retained histories, implicit registries, or automatic downloads.
