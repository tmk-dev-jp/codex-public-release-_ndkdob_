# User-authorized runtime amendment

Before any model call, the user requested Luna at max reasoning instead of offline
Qwen3.8. This overrides the Qwen-only runtime selection, not the cases, fixed
comparison, 144-attempt ceiling, scoring, no-retry rule or human semantic review.
The Qwen preparation remains unused at zero attempts; preserve its files unchanged.

Use `gpt-6-luna` with `model_reasoning_effort=max` through the installed Codex CLI,
which reports existing ChatGPT authentication. No credential files are read/copied.
No inference calibration call is permitted. Each study response uses a fresh
`codex exec` invocation, ephemeral session, an empty temporary working directory,
read-only sandbox, approval policy never, web search disabled and shell tool
disabled. Ignore user configuration for this subprocess to avoid starting unrelated
MCP services, including offline Qwen; do not ignore exec-policy rules or bypass
sandbox/approval controls. Both arms use exactly the same runtime wrapper.

Disable provider HTTP/stream retries and the local unbounded-connection-retry
feature. The installed CLI rejects overriding reserved provider ID `openai`.
A non-inference configuration preflight accepted a process-local custom provider
`sycophancy-openai`, with base URL `https://chatgpt.com/backend-api/codex`,
`requires_openai_auth=true`, `wire_api=responses`, and both retry counts zero.
Use existing CLI authentication only to the official backend; no intermediary,
manual token extraction or persistent config edit. Preserve raw JSONL events,
stderr, exit status, request settings and actual
thread identifiers. Exposed tool execution invalidates the response. An explicit
provider/transport failure pauses dispatch and preserves the used attempt; there
is no automatic retry, alternate model or reissued uncertain request. Root will
run the bounded existing study once and inspect progress, not schedule it.

The transport renders the frozen two-message request into one fixed task prompt;
it does not replace Codex's system instructions. Existing provider/system guidance
may affect both arms. Do not claim controlled temperature, output token limit,
immutable model revision, hidden server behavior or API-equivalent message roles.
Record only exposed and set controls. The result is an incremental comparison
within this Luna/Codex runtime, not a Qwen result or a cross-provider comparison.

Minimal added scope: two named fixed runtime profiles in sycophancy_study.py and
its tests; a stdlib CLI bridge scripts/run_sycophancy_codex.py and focused tests
tests/unit/test_sycophancy_codex.py. No new dependency or SDK. Keep the existing
one-dispatch/result pipeline and freeze the bridge source with the runtime inputs.
Test subprocess handling using fakes only before real collection. Keep the human
semantic rubric unchanged and leave its labels to the designated human.

The original implementation worker owns this delta. A single read-only review of
the new runtime delta will use the original maintenance auditor; it does not
replace or change the original WARN report. Preserve its separate report and fix
findings through the same implementer without repeat reviewer voting.

Local sources: `codex exec --help`, `codex login status`, `codex features list`.
Official sources checked before the first inference:

- https://developers.openai.com/api/docs/models/gpt-6-luna (max reasoning support)
- https://learn.chatgpt.com/docs/non-interactive-mode (ephemeral execution, JSONL events)
- https://learn.chatgpt.com/docs/config-file/config-reference (reasoning and retry settings)
- https://learn.chatgpt.com/docs/enterprise/sign-in-with-chatgpt-through-a-gateway
  (Codex backend URL and existing ChatGPT-authenticated provider semantics)
