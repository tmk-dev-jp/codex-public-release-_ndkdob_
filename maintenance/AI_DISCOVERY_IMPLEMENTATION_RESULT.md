# Scientific contribution contract: implementation evidence

Date: 2026-10-22. Maintenance only; no live experiment or model settings changed.

## Changes

- `scripts/new_experiment.py` marks newly created manifests with
  `novelty_contract_version: "1.0"`.
- `scripts/research_memory.py` validates versioned contributions, 1-3 distinct
  source observations against exact closest-work identifiers, required text,
  supported kinds and different normalized predictions. Supplied contributions
  are validated in legacy histories too; absent legacy contributions remain valid.
  Unsupported versions and malformed structures return explicit validation errors.
- `scripts/next_autonomous_step.py` requires contributions for marked novelty
  routes. Existing source-count and output budgets remain unchanged.
- `scripts/build_plan_review_bundle.py` validates marked contribution evidence
  when computing existing audit inputs. Bundle creation, audit acceptance and the
  accepted-audit prerequisite used by direct approval therefore share the gate.
  Marked bundles expose the contract version and hash it; absent markers preserve
  historical hash shapes. The existing complete novelty hash binds contributions.
- `scripts/research_decision.py` conditionally includes the marker in decision
  snapshots and rejects incomplete new novelty responses before acceptance writes.
- `tests/unit/test_scientific_contribution.py` covers the marked and legacy paths,
  malformed data, source provenance, audit/decision invalidation, and mutation-free
  rejection. Existing test fixtures were not changed.

## Verification

| Check | Observed result |
| --- | --- |
| New contribution tests plus `test_research_memory`, `test_plan_audit`, `test_agent_led_loop`, `test_autonomous_loop` | 261 passed |
| `<historical-test-environment>/bin/python -m pytest tests/unit tests/smoke -k 'not SandboxTests' -o addopts='' -q` | 648 passed, 2 existing sandbox-dependent cases deselected, 13 subtests passed |
| `python3 scripts/validate.py` | `OK validate files=2334 warnings=0` |
| Ruff on the five changed runtime files and new test file, `--ignore E402` | Passed; the ignore preserves existing script import-path bootstraps |
| Scoped `git diff --check` | Passed |
| Complete synthetic source-grounded novelty response | 181 words; passed actual prepare, dispatch, bind-worker and accept APIs under the unchanged 250-word limit |
| Missing contribution, invented source, malformed contribution/record/risk, identical predictions | Rejected with state, manifest and novelty history bytes unchanged and no APPLYING/ACCEPTED markers |
| Changed contribution or removed version marker | Existing accepted audit and pending decision rejected |
| Historical unmarked novelty and accepted audit | Readable and usable without rewriting history or adding hash fields |

An initial run exposed two errors in the new fixtures (incorrect approval source
name and aliased observation lists). Both were corrected before the passing runs.
The final full regression includes the subsequent malformed-risk guard and test
formatting corrections. No test failure was bypassed by changing an acceptance
criterion, source budget or output limit.

## Limits and integration

These tests establish structural/provenance enforcement, not semantic correctness,
global novelty or improved scientific discovery. The synthetic source summaries
are fixtures and supply no scientific evidence. Replication classifications remain
claims whose supporting-only scope must be assessed independently. Different
wording in predictions does not prove a discriminating scientific contrast.

The supervisor owns guidance, skill checks, final live-input hash comparison and
maintenance handoff. This worker changed only the five assigned runtime files,
the new test module and this result record; research data/state were not edited.
