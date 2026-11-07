The smallest fix belongs in `export_v2()`; no validator, study orchestration, or bridge change is needed.

Evidence and flow:

- `scripts/evaluate_sycophancy.py:293` builds prompts with `[ID]` source headings and unmarked semantic section labels. The instructions say “Cite decisive source IDs”; `response_schema.citations` is merely `["source ID"]`.
- `validate_v2_response()` at line 359 accepts exact bare keys from `baseline_evidence ∪ semantic.passages` and rejects duplicates or unknown strings. All 12 current cases have `RULE`, `FACTS`, `AUDIT`, `SYNTHETIC_SOURCE`. Fixture loading already requires baseline and changed evidence IDs to match.
- `scripts/sycophancy_study.py:107`, `requests_for()`, embeds the same exported prompt/schema in both arms; only system policy and opaque request ID differ.
- `scripts/run_sycophancy_codex.py:80`, `render_prompt()`, JSON-wraps the supplied messages unchanged.
- `classify()` at `scripts/sycophancy_study.py:431` calls `validate_v2_response()` and preserves invalid classification.

Recommended patch:

1. In every v2 prompt, enumerate the allowed IDs dynamically from the evidence and semantic passage keys, formatted as quoted bare strings.
2. State explicitly that citations must use those exact strings, without displayed square brackets; prompt section labels, including Candidate prediction, Alternative prediction and Test context, are not source IDs.
3. Clarify the v2 schema placeholder to refer to the prompt’s allowed bare IDs. Keep citation selection discretionary; do not instruct models to cite every allowed source.

Existing tests to extend:

- `test_v2_exact_scope_opaque_ids_and_matched_manipulations`: exact allowed enumeration in all 72 prompts; explicit bracket/section-label distinction; existing matched-control assertions remain.
- `test_v2_rejects_bad_batches`: bracketed valid IDs and the three observed section labels still reject. A focused positive case should establish that bare valid IDs still accept.
- `test_prepare_is_offline_fixed_order_and_only_policy_differs`: contract survives freezing and remains identical across A/B after substituting request IDs.
- `test_frozen_asset_source_and_code_provenance`: retain source/asset rejection; cover changed exported contract if needed.
- Bridge coverage already verifies actual process input equals `render_prompt(requests[0]["messages"])`; no bridge modification is justified.

Preservation issue: `verify()` binds original source-path hashes (line 238), regenerated prompt digest (253), executing code hashes (255–263), and regenerated requests (273). Editing the evaluator will therefore prevent the current checkout from verifying old runs, even with untouched old artifacts. Preserve exact pre-edit source bytes and record historical verification first; document that historical execution needs the matching preserved code/source layout. Do not rewrite frozen manifests or weaken verification to accommodate the new export.

`LUNA_RESULT.md` supports a format-contract ambiguity and an unscorable completed comparison. It does not establish semantic errors or show that revised instructions will eliminate failures. No raw responses were inspected, files edited, or models called.
