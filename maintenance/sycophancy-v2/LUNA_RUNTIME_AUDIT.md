**Luna runtime-delta verdict: WARN — fix transport-validation failure accounting before collection.** This is a separate assessment of the new runtime delta; it does not replace or revise the original implementation WARN report.

1. **P2: Final-file/event binding failures do not pause collection.**  
   In `scripts/run_sycophancy_codex.py:137–146`, `_capture()` detects a missing final-message file/event or disagreement between them, but records only `output_validation_error`. With exit status zero, `isError` remains false. The result becomes `returned-invalid`, and `run_study()` at lines 208–212 continues because it stops only for `provider-error`.

   I reproduced this entirely with a mocked subprocess: it emitted valid JSONL containing a valid response and `turn.completed`, returned zero, and wrote different contents to the final-message file. The first attempt recorded:
   ```text
   state = returned-invalid
   output_validation_error = last-message file differs from last agent event
   ```
   A second invocation dispatched successfully without external resolution. Two attempts were consumed, with zero provider errors reported.

   This is a detected failure of the transport’s binding contract, distinct from malformed model-authored JSON. Continuing can exhaust the fixed attempt budget while the bridge is malfunctioning. Partial or favorable scoring remains blocked.

   **Correction:** classify missing or mismatched final-file/event binding as a transport failure that pauses dispatch, retaining all raw bytes and the consumed attempt. Update `tests/unit/test_sycophancy_codex.py:130–140`, which currently expects mismatch to be an ordinary invalid response. Add the next-dispatch-blocked assertion. Keep correctly bound but malformed model JSON as `returned-invalid`, without repair or retry.

The remaining inspected delta is consistent with the amendment:

- The command fixes `gpt-6-luna`, max reasoning, ephemeral execution, an empty temporary working directory, read-only sandbox, approval policy `never`, disabled shell/web access, and zero configured HTTP/stream retries with unbounded connection retries disabled.
- Both arms use the same transport and fresh subprocess invocation. The wrapper explicitly describes rendered message roles as task data, and the Luna profile does not claim temperature or token-limit control.
- The process-local provider specifies the official Codex backend and existing OpenAI authentication. The bridge contains no credential-file access, manual token handling, persistent configuration edits, alternate-model fallback, sandbox bypass, or ignored execution-policy flag.
- Runtime settings, bridge source, command arguments, wrapper, timeout, and selected executable hash are frozen and verified. The launcher-only hash limitation is explicitly disclosed.
- Raw stdout/stderr bytes, final-file bytes, exit status, request identity/settings, command, timestamps, events, and observed thread identifiers are retained. Explicit process/provider failures stop the loop; exposed tool activity invalidates responses. Dispatch precedes subprocess execution, and uncertain or failed requests are not reissued.

All eight recorded scope hashes and the dispatch-request hash matched. I read the two Luna amendment/preflight documents, the plan’s runtime amendment, audit request/dispatch records, the complete new bridge and its tests, `sycophancy_study.py` lines 1–561 and 808–883, and the relevant updated study tests at lines 175–250 and 355–411. The unchanged evaluator was hash-checked, not reread.

I ran one isolated fake-subprocess reproduction, with no real executable invocation, model/network calls, credential access, repository edits, or real study artifacts. Account-level access and actual inference connectivity remain unverified until the first authorized study attempt.
