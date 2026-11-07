---
name: set-subagent-defaults
description: Set, inspect, or clear the default model and optional reasoning effort for Codex subagents in project configuration.
---

Use maintenance routing. Default to this repository's `.codex/config.toml`; edit user-global configuration only when explicitly requested. Creating this skill does not select a model.

1. List the target configuration path, then inspect its existing `[agents]` defaults. Read only relevant role files when explaining an override; do not load research records or unrelated configuration/secrets.
2. For a change, use the exact model requested by the user and optional reasoning effort. Ask for a missing model only when setting it; inspection and clearing need no model. Check the current host's model availability and supported effort when available. Do not silently substitute a model or claim access was verified without evidence.
3. Edit only `[agents].default_subagent_model` and, if requested, `default_subagent_reasoning_effort`. Add `[agents]` if absent without duplicating tables or keys. Preserve other tables, comments, permissions, hooks, thread limits and role settings. Model-only requests preserve existing effort; if it is incompatible, ask which supported effort to use before writing. Clearing removes only the requested key(s), allowing inherited/default configuration to apply; an empty string is not a reset.
4. Parse the resulting TOML with an available parser and inspect the exact diff. For this repository run `python3 scripts/validate.py`. Report the target path, before/after values, retained overrides, and checks. Do not spawn a paid verification agent without a request.

Explicit spawn settings and custom role files can override these defaults. Do not rewrite the parent model, pinned planner/auditor models, implementation profiles, or active experiment locks to make a default apply. Explain that running agents retain their settings; use a new chat after configuration reload to verify new subagents.

Use the current [official subagent documentation](https://learn.chatgpt.com/docs/agent-configuration/subagents) if precedence or supported settings are unclear.
