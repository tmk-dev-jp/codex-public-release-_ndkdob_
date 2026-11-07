# Research-minimal code policy

## Purpose

Optimize for fast, interpretable experiments rather than production-grade fault tolerance.

## Decision ladder

Apply this only after tracing the scoped behavior. Stop at the first option that satisfies the locked plan:

1. Avoid code when the requirement is already met or unnecessary.
2. Reuse an existing helper, type, or established pattern.
3. Use the standard library or a native platform feature.
4. Use an already-installed dependency.
5. Write the minimum new code.

Do not add a speculative abstraction or dependency. For a repair, inspect callers within scope and fix the shared root cause once; request plan revision before crossing scope.

For a scientific change, preserve the declared baseline behavior outside the intervention point and modify only the candidate path/symbol targets. The shared-root-cause rule applies only to behavior-preserving repairs. If a broader scientific mechanism is needed, revise and relock the plan instead of folding it into implementation.

## Keep

- Checks that prevent invalid scientific results: configuration mismatch, data leakage, shape mismatch, empty splits, non-finite loss or gradients, incompatible metrics, stale config, and stale implementation hashes.
- Existing trust-boundary validation, data-loss prevention, security controls, accessibility behavior, and explicitly requested behavior.
- Focused tests for stable component contracts and previously observed code failures.
- One outer CLI exception adapter that emits a compact final error.

## Avoid

- Automatic retries, silent fallback to another model, dataset, split, device, or metric.
- Broad internal `try/except` blocks, deep custom exception hierarchies, speculative validation, and defensive wrappers around trusted library calls.
- Progress bars, batch or epoch logs, tensor dumps, retained histories, telemetry, and permanent debug switches.
- General refactoring or abstractions unrelated to the locked hypothesis.

## Debugging

Use the smallest reproducer, add temporary instrumentation only when necessary, and remove it before `mark-implemented`. Preserve only `error.json` and a focused regression test when recurrence is plausible.

Production deployment, security-sensitive input, distributed recovery, and long-running service concerns require a separate hardening phase and are outside this research template.
