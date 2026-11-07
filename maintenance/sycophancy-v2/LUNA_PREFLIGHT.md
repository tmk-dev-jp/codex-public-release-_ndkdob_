# Luna preflight evidence

No inference request was made in these checks.

- `codex login status`: logged in using ChatGPT. Credential contents were not read.
- `codex exec --help`: supports ephemeral non-interactive execution, stdin prompts,
  JSONL event output, model selection, read-only sandbox and user-config isolation.
- `codex debug models --bundled`: `gpt-6-luna` exists and lists `max` reasoning.
- Configuration parsing rejected retry overrides under reserved provider `openai`.
- Configuration parsing accepted the process-local provider `sycophancy-openai`,
  official Codex backend URL, existing OpenAI authentication, Responses protocol,
  request/stream retry counts zero, max reasoning and approval policy never.
- `features list` with that configuration confirmed `shell_tool=false` and
  `unbounded_connection_retries=false`. Web search was configured disabled.

These local checks establish CLI argument/configuration support only. They do not
establish account-level model access, actual inference connectivity, server-side
isolation or unobserved retry behavior. The first prescribed study attempt is the
first inference call; no extra model calibration or availability query is planned.
The frozen bridge and settings, rather than this prose, determine execution.
