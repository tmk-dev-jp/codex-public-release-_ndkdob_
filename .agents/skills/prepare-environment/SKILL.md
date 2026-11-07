---
name: prepare-environment
description: Check local dependencies and repository readiness when preparing the environment for research setup.
---

# Prepare Environment

Use this before project-specific setup. Do not edit research intent, data manifests, source code, or experiment records unless the user explicitly asks for a repair after a failed check.

## Read

- Python/dependencies: `pyproject.toml` and installed-package checks.
- Git tracking: status; `.gitignore` only for tracking issues.
- Hook readiness: `.codex/config.toml` and `.codex/hooks.json`.
- Research readiness: `research/CONTEXT.md` and validator output.
- Setup command help: relevant section of `human/QUICKSTART.ja.md`.

Read only the categories needed for the requested check.

## Procedure

1. Inspect `git status --short` and report whether the tree is clean or has existing user changes.
2. Check Python availability with `python --version` and `python3 --version`; prefer the command that exists in the environment.
3. Check package import availability and run `python3 scripts/validate.py` for repository readiness. Run relevant tests when verifying a repair; use the full suite only when a full environment check is requested and dependencies are installed.
4. If dependencies are missing, use the manual's setup commands. Install only when the request authorizes environment installation; existing authorization needs no repeated confirmation.
5. Inspect hook configuration and explain whether hooks are enabled; do not change trust or hook settings automatically.
6. Report Git initialization status. Recommend `git init`, `git add .`, and the first commit only when no repository history exists.

## Boundaries

- Do not create an active experiment.
- Do not run training, data processing, downloads, or package installation by default.
- Do not mutate raw data, generated artifacts, or research state.
- Keep output concise: confirmed environment facts, failed checks, and next command.
