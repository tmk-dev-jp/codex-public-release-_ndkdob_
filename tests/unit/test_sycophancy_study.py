from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from scripts.common import atomic_write_json, read_json, sha256_file
from scripts.evaluate_sycophancy import DIMENSIONS, digest, export_prompts, v2_items, write_new_json
from scripts.sycophancy_study import (
    COMMON_SYSTEM,
    SETTINGS,
    collect,
    dispatch,
    human_packet,
    materialize,
    prepare,
    record_result,
    resolve_failure,
    score,
    validate_review,
    verify,
    verify_batch,
)

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests/fixtures/sycophancy/cases-v2.json"
POLICY = ROOT / "automation/INDEPENDENT_JUDGMENT.md"
ATTESTATION = (
    "I am the designated human assessor and personally reviewed these "
    "responses without model-generated labels."
)


def _prepare(tmp_path):
    directory = tmp_path / "study"
    prepare(directory, FIXTURE, POLICY)
    return directory


def _response(request, case):
    return {
        "id": request["id"],
        "verdict": case["expected"]["changed" if request["variant"] == "changed" else "baseline"],
        "citations": case["required_sources"],
        "rationale": "Numerical rule applied; " + request["id"],
        "audit_authority": "preserved",
        "source_entailment": {
            "assessment": "supported"
            if case["semantic_expected"]["source_entailment"]
            else "unsupported",
            "explanation": "Synthetic unit-test explanation.",
        },
        "prediction_distinguishability": {
            "assessment": "distinct"
            if case["semantic_expected"]["prediction_distinguishability"]
            else "equivalent",
            "explanation": "Synthetic unit-test explanation.",
        },
    }


@pytest.fixture(scope="module")
def complete_study(tmp_path_factory):
    directory = _prepare(tmp_path_factory.mktemp("complete-study"))
    _, fixture, requests = verify(directory)
    cases = {c["id"]: c for c in fixture["cases"]}
    for sequence, request in enumerate(requests):
        # Direct immutable test events avoid repeatedly exercising expensive frozen-source
        # verification 144 times. Dispatch/record APIs are covered independently below.
        event = {
            "id": request["id"],
            "sequence": sequence,
            "at": "2026-10-23T00:00:00+00:00",
            "frozen_sha256": sha256_file(directory / "frozen.json"),
            "request_sha256": digest(request),
        }
        path = directory / "dispatch" / (request["id"] + ".json")
        write_new_json(path, event)
        raw = json.dumps(
            {
                "model": "offline-test-double",
                "runtime_id": "test-v1",
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(_response(request, cases[request["case_id"]])),
                    }
                ],
            }
        )
        write_new_json(
            directory / "results" / (request["id"] + ".json"),
            {
                "id": request["id"],
                "at": event["at"],
                "frozen_sha256": event["frozen_sha256"],
                "dispatch_sha256": sha256_file(path),
                "raw": raw,
                "raw_sha256": hashlib.sha256(raw.encode()).hexdigest(),
                "pointer": ["content", 0, "text"],
                "kind": "returned",
            },
        )
    batch_path = directory / "batch.json"
    materialize(directory, batch_path)
    return directory, batch_path


def test_prepare_is_offline_fixed_order_and_only_policy_differs(tmp_path):
    directory = _prepare(tmp_path)
    frozen, fixture, requests = verify(directory)
    assert len(requests) == 144
    assert len({r["id"] for r in requests}) == 144
    assert {r["arm"] for r in requests[:2]} == {"A", "B"}
    assert [r["arm"] for r in requests[:4]] == ["A", "B", "B", "A"]
    assert SETTINGS["temperature"] == 0 and SETTINGS["max_iterations"] == 1
    assert frozen["availability_at_preparation"].startswith("offline")
    exported = export_prompts(fixture)
    for pair in range(72):
        items = requests[pair * 2 : pair * 2 + 2]
        a = next(r for r in items if r["arm"] == "A")
        b = next(r for r in items if r["arm"] == "B")
        assert a["messages"][0]["content"] == COMMON_SYSTEM + "\n\n" + POLICY.read_text()
        assert b["messages"][0]["content"] == COMMON_SYSTEM
        assert a["messages"][1]["content"].replace(a["id"], b["id"]) == b["messages"][1]["content"]
        payload = json.loads(a["messages"][1]["content"])
        assert payload["prompt"] == exported["prompts"][pair]["prompt"]
        assert payload["response_schema"] == exported["response_schema"]
        assert "Allowed citation strings (exact, bare IDs): " in payload["prompt"]
        assert "this description is not a citation" in payload["response_schema"]["citations"][0]
        assert all(
            key not in a["messages"][1]["content"]
            for key in ("semantic_expected", "premise_annotations", "user-01", str(FIXTURE))
        )
    _, _, _, status = collect(directory)
    assert status["planned"] == 144 and status["attempts"] == 0
    assert status["counts"]["not-dispatched"] == 144
    assert not status["scorable"]
    with pytest.raises(ValueError, match="offline"):
        dispatch(directory)
    with pytest.raises(FileExistsError):
        prepare(directory, FIXTURE, POLICY)
    with pytest.raises(ValueError, match="unscorable"):
        materialize(directory, tmp_path / "partial.json")
    assert len(list(v2_items(fixture))) == 72


def test_dispatch_once_capture_envelope_and_invalid_without_repair(tmp_path):
    directory = _prepare(tmp_path)
    payload = dispatch(directory, availability_confirmed=True)
    _, fixture, requests = verify(directory)
    assert payload["id"] == requests[0]["id"]
    _, _, _, status = collect(directory)
    assert status["attempts"] == 1 and status["counts"]["dispatched-without-result"] == 1
    with pytest.raises(ValueError, match="never reissue"):
        dispatch(directory, availability_confirmed=True)
    raw = tmp_path / "provider.json"
    response = _response(requests[0], fixture["cases"][0])
    envelope = {
        "model": "test-double",
        "runtime_id": "frozen-test",
        "content": [{"type": "text", "text": json.dumps(response)}],
    }
    raw.write_bytes((json.dumps(envelope) + "\r\n").encode())
    outcome = record_result(directory, payload["id"], raw, ["content", 0, "text"])
    assert outcome["state"] == "returned-valid"
    saved = read_json(directory / "results" / (payload["id"] + ".json"))
    assert saved["raw"].encode() == raw.read_bytes()
    with pytest.raises(ValueError, match="only once"):
        record_result(directory, payload["id"], raw, ["content", 0, "text"])
    second = dispatch(directory, availability_confirmed=True)
    raw.write_text("not json")
    assert record_result(directory, second["id"], raw)["state"] == "returned-invalid"
    _, _, _, status = collect(directory)
    assert status["counts"]["returned-valid"] == status["counts"]["returned-invalid"] == 1
    assert not status["scorable"]
    assert status["runtime_identifiers"][0]["runtime_id"] == "frozen-test"


@pytest.mark.parametrize("explicit", [True, False])
def test_provider_error_stops_dispatch_until_external_resolution(tmp_path, explicit):
    directory = _prepare(tmp_path)
    payload = dispatch(directory, availability_confirmed=True)
    raw = tmp_path / "error.json"
    raw.write_text(json.dumps({"isError": True, "error": "offline"}))
    assert (
        record_result(directory, payload["id"], raw, provider_error=explicit)["state"]
        == "provider-error"
    )
    with pytest.raises(ValueError, match="external resolution"):
        dispatch(directory, availability_confirmed=True)
    resolve_failure(
        directory, payload["id"], "Synthetic test of an external resolution; no real provider used."
    )
    second = dispatch(directory, availability_confirmed=True)
    assert second["id"] != payload["id"]
    assert collect(directory)[3]["counts"]["provider-error"] == 1


@pytest.mark.parametrize("explicit", [True, False])
def test_provider_failure_with_tool_activity_still_pauses_dispatch(tmp_path, explicit):
    directory = _prepare(tmp_path)
    payload = dispatch(directory, availability_confirmed=True)
    raw = tmp_path / "combined-error.json"
    envelope = {
        "isError": True,
        "error": "provider connection failed",
        "tool_calls": [{"name": "unexpected_tool"}],
        "runtime_id": "test-runtime",
    }
    raw.write_text(json.dumps(envelope))
    outcome = record_result(directory, payload["id"], raw, provider_error=explicit)
    assert outcome == {
        "state": "provider-error",
        "exposed_tool_activity": True,
        "runtime": {"runtime_id": "test-runtime"},
    }
    saved_path = directory / "results" / (payload["id"] + ".json")
    saved = saved_path.read_bytes()
    assert json.loads(read_json(saved_path)["raw"]) == envelope
    status = collect(directory)[3]
    assert status["attempts"] == 1
    assert status["counts"]["provider-error"] == 1
    assert status["details"][0]["exposed_tool_activity"] is True
    assert not status["scorable"]
    with pytest.raises(ValueError, match="external resolution"):
        dispatch(directory, availability_confirmed=True)
    with pytest.raises(ValueError, match="only once"):
        record_result(directory, payload["id"], raw, provider_error=explicit)
    resolve_failure(directory, payload["id"], "Synthetic external resolution; no provider used.")
    second = dispatch(directory, availability_confirmed=True)
    assert second["id"] == verify(directory)[2][1]["id"]
    assert second["id"] != payload["id"]
    assert saved_path.read_bytes() == saved
    with pytest.raises(ValueError, match="never reissue"):
        dispatch(directory, availability_confirmed=True)
    with pytest.raises(ValueError, match="only once"):
        record_result(directory, payload["id"], raw, provider_error=explicit)


@pytest.mark.parametrize(
    "activity",
    [
        {"tool_calls": [{"name": "exec"}]},
        {"content": [{"type": "tool_use", "name": "exec"}]},
        {"tools_invoked": True},
    ],
)
def test_exposed_tool_activity_is_invalid(tmp_path, activity):
    directory = _prepare(tmp_path)
    payload = dispatch(directory, availability_confirmed=True)
    raw = tmp_path / "tools.json"
    raw.write_text(json.dumps(activity))
    assert record_result(directory, payload["id"], raw)["reason"] == "exposed tool activity"
    assert any("unverified" in x for x in collect(directory)[3]["limitations"])


def test_frozen_asset_source_and_code_provenance(tmp_path):
    fixture_copy = tmp_path / "fixture.json"
    fixture_copy.write_bytes(FIXTURE.read_bytes())
    directory = tmp_path / "study"
    prepare(directory, fixture_copy, POLICY)
    original = fixture_copy.read_bytes()
    fixture_copy.write_bytes(original + b" ")
    with pytest.raises(ValueError, match="source changed"):
        verify(directory)
    fixture_copy.write_bytes(original)
    requests = read_json(directory / "requests.json")
    requests[0]["messages"][0]["content"] += "Changed"
    atomic_write_json(directory / "requests.json", requests)
    with pytest.raises(ValueError, match="asset changed"):
        verify(directory)


def test_batch_exact_provenance_complete_and_no_overwrite(complete_study, tmp_path):
    directory, batch_path = complete_study
    fixture, batch = verify_batch(directory, batch_path)
    assert len(batch["arms"]["A"]) == len(batch["arms"]["B"]) == 72
    result = score(directory, batch_path, tmp_path / "scores.json")
    assert not result["comparison"]["favorable"]
    assert result["human_review"].startswith("pending")
    for defect in ("run", "answer", "missing", "duplicate"):
        bad = deepcopy(batch)
        if defect == "run":
            bad["provenance"]["run_id"] = "different"
        elif defect == "answer":
            bad["arms"]["A"][0]["rationale"] += " repaired"
        elif defect == "missing":
            bad["arms"]["A"].pop()
        else:
            bad["arms"]["A"][-1] = bad["arms"]["A"][0]
        path = tmp_path / (defect + ".json")
        write_new_json(path, bad)
        with pytest.raises(ValueError, match="provenance"):
            verify_batch(directory, path)
    aliases = [
        batch_path,
        directory / "fixture.json",
        directory / "requests.json",
        directory / "policy.json",
        directory / "frozen.json",
    ]
    alias = tmp_path / "symlink.json"
    alias.symlink_to(batch_path)
    hardlink = tmp_path / "hardlink.json"
    hardlink.hardlink_to(batch_path)
    for path in [*aliases, alias, hardlink]:
        with pytest.raises(ValueError, match="overwrite"):
            score(directory, batch_path, path)
    assert fixture["schema_version"] == 2


def test_human_packet_masking_shuffle_attribution_and_validation(complete_study, tmp_path):
    directory, batch_path = complete_study
    output = tmp_path / "human"
    human_packet(directory, batch_path, output, "Designated test assessor")
    packet_path = output / "packet.json"
    packet = read_json(packet_path)
    mapping = read_json(directory / "human-mapping.json")
    text = packet_path.read_text()
    assert len(packet["items"]) == 144
    assert [r["id"] for r in packet["items"]] != [r["human_id"] for r in mapping["mapping"]]
    assert not any(
        key in text
        for key in (
            "user-01",
            "peer-01",
            "base_id",
            "request_id",
            "semantic_expected",
            "premise_annotations",
            "runtime_id",
            "offline-test-double",
        )
    )
    assert all(m["request_id"] not in text for m in mapping["mapping"])
    assert all("id" not in r["response"] for r in packet["items"])
    assert all("[routing ID]" in r["response"]["rationale"] for r in packet["items"])
    review = read_json(output / "review-template.json")
    review_path = tmp_path / "human-review.json"
    atomic_write_json(review_path, review)
    with pytest.raises(ValueError, match="actual designated human"):
        validate_review(directory, batch_path, packet_path, review_path)
    review.update(attestation=ATTESTATION, reviewed_at="2026-10-23T00:00:00+00:00")
    for row in review["items"]:
        for d in DIMENSIONS:
            row[d]["explanation"] = "Synthetic test judgment only; not an actual review."
    atomic_write_json(review_path, review)
    validated = validate_review(directory, batch_path, packet_path, review_path)
    assert len(validated["arms"]["A"]) == 72
    result = score(directory, batch_path, tmp_path / "unresolved.json", packet_path, review_path)
    assert not result["comparison"]["favorable"]
    assert not result["comparison"]["checks"]["semantics_complete"]
    for defect in ("duplicate", "unknown", "missing", "assessor", "packet", "explanation"):
        bad = deepcopy(review)
        if defect == "duplicate":
            bad["items"][-1] = bad["items"][0]
        elif defect == "unknown":
            bad["items"][0]["id"] = "unknown"
        elif defect == "missing":
            bad["items"].pop()
        elif defect == "assessor":
            bad["assessor"] = "Another assessor"
        elif defect == "packet":
            bad["packet_sha256"] = "other"
        else:
            bad["items"][0][DIMENSIONS[0]]["explanation"] = ""
        atomic_write_json(review_path, bad)
        with pytest.raises(ValueError):
            validate_review(directory, batch_path, packet_path, review_path)
    # Mapping swaps cannot route an assessor's labels to the other arm.
    altered_mapping = deepcopy(mapping)
    altered_mapping["mapping"][0]["arm"] = "B" if mapping["mapping"][0]["arm"] == "A" else "A"
    atomic_write_json(directory / "human-mapping.json", altered_mapping)
    try:
        with pytest.raises(ValueError, match="frozen mapping"):
            validate_review(directory, batch_path, packet_path, review_path)
    finally:
        atomic_write_json(directory / "human-mapping.json", mapping)


def test_collection_provenance_rejects_cross_run_and_mutated_raw(tmp_path):
    first = _prepare(tmp_path / "first")
    second = _prepare(tmp_path / "second")
    payload = dispatch(first, availability_confirmed=True)
    raw = tmp_path / "raw.json"
    raw.write_text("invalid result retained")
    record_result(first, payload["id"], raw)
    result_path = first / "results" / (payload["id"] + ".json")
    original = read_json(result_path)
    altered = deepcopy(original)
    altered["raw"] = "{}"
    atomic_write_json(result_path, altered)
    with pytest.raises(ValueError, match="raw provider record"):
        collect(first)
    atomic_write_json(result_path, original)
    copied_dispatch = read_json(first / "dispatch" / (payload["id"] + ".json"))
    second_id = dispatch(second, availability_confirmed=True)["id"]
    copied_dispatch["id"] = second_id
    atomic_write_json(second / "dispatch" / (second_id + ".json"), copied_dispatch)
    with pytest.raises(ValueError, match="provenance mismatch"):
        collect(second)


def test_runtime_profile_is_strict_and_qwen_defaults_remain_compatible(tmp_path):
    with pytest.raises(ValueError, match="unknown runtime"):
        prepare(tmp_path / "bad", FIXTURE, POLICY, "arbitrary-model")
    with pytest.raises(ValueError, match="only supported"):
        prepare(tmp_path / "bad-executable", FIXTURE, POLICY, executable=Path("/tmp/fake"))
    directory = _prepare(tmp_path)
    frozen, _, _ = verify(directory)
    assert frozen["runtime_profile"] == "qwen38"
    assert read_json(directory / "settings.json") == SETTINGS
    assert "transport.json" not in frozen["assets"]
