from __future__ import annotations

import base64
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.common import read_json
from scripts.run_sycophancy_codex import (
    ARGUMENTS,
    CUSTOM_PROVIDER,
    PROMPT_WRAPPER,
    render_prompt,
    run_next,
    run_study,
)
from scripts.sycophancy_study import collect, prepare, resolve_failure, verify

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests/fixtures/sycophancy/cases-v2.json"
POLICY = ROOT / "automation/INDEPENDENT_JUDGMENT.md"


def prepared(tmp_path):
    executable = tmp_path / "fake-codex"
    executable.write_text("This is a non-executable test fixture; subprocess is always mocked.")
    directory = tmp_path / "study"
    prepare(directory, FIXTURE, POLICY, "luna-max", executable)
    return directory


def fake_process(monkeypatch, mode="success"):
    calls = []

    def run(command, **kwargs):
        calls.append((command, kwargs))
        assert list(Path(kwargs["cwd"]).iterdir()) == []
        assert kwargs["check"] is False and kwargs["timeout"] == 900
        assert kwargs["capture_output"] is True
        stdin = kwargs["input"].decode()
        assert stdin.startswith(PROMPT_WRAPPER)
        messages = json.loads(stdin[len(PROMPT_WRAPPER) :])["messages"]
        request = json.loads(messages[1]["content"])
        response = {
            "id": request["id"],
            "verdict": "support",
            "citations": ["RULE", "FACTS", "AUDIT"],
            "rationale": "Synthetic transport test response.",
            "audit_authority": "preserved",
            "source_entailment": {"assessment": "supported", "explanation": "Test."},
            "prediction_distinguishability": {"assessment": "distinct", "explanation": "Test."},
        }
        text = "not json" if mode == "invalid-json" else json.dumps(response)
        events = [{"type": "thread.started", "thread_id": "test-thread"}]
        if mode in ("tool", "combined"):
            events.append(
                {
                    "type": "item.completed",
                    "item": {"type": "command_execution", "command": "unexpected"},
                }
            )
        if mode != "missing-event":
            events.append(
                {"type": "item.completed", "item": {"type": "agent_message", "text": text}}
            )
        events.append(
            {"type": "turn.failed", "error": {"message": "provider failed"}}
            if mode in ("provider", "combined")
            else {"type": "turn.completed", "usage": {"output_tokens": 1}}
        )
        stdout = ("\n".join(json.dumps(e) for e in events) + "\n").encode()
        stderr = b"Exact stderr, including CRLF.\r\n"
        if mode == "timeout":
            raise subprocess.TimeoutExpired(command, 900, output=stdout, stderr=stderr)
        if mode == "launch":
            raise OSError("synthetic launch failure")
        final_path = Path(command[command.index("-o") + 1])
        if mode != "missing-file":
            final_path.write_bytes((text + (" wrong" if mode == "mismatch" else "\n")).encode())
        return SimpleNamespace(
            stdout=stdout, stderr=stderr, returncode=1 if mode == "process" else 0
        )

    monkeypatch.setattr("scripts.run_sycophancy_codex.subprocess.run", run)
    return calls


def test_luna_profile_and_fixed_transport_are_frozen(tmp_path):
    directory = prepared(tmp_path)
    frozen, _, requests = verify(directory)
    settings = read_json(directory / "settings.json")
    assert frozen["runtime_profile"] == "luna-max"
    assert settings["advertised_model"] == "gpt-6-luna"
    assert settings["model_reasoning_effort"] == "max"
    assert not {"temperature", "max_tokens", "max_iterations", "tool"} & set(settings)
    assert "bridge" in frozen["sources"] and "transport.json" in frozen["assets"]
    assert len(requests) == 144 and collect(directory)[3]["attempts"] == 0
    assert "model_providers.openai." not in " ".join(ARGUMENTS)
    assert CUSTOM_PROVIDER in ARGUMENTS
    assert all(
        flag in ARGUMENTS
        for flag in ("--ignore-user-config", "--ephemeral", "--json", "--skip-git-repo-check")
    )
    assert "--ignore-rules" not in ARGUMENTS
    assert not any("bypass" in a for a in ARGUMENTS)
    assert "unbounded_connection_retries" in ARGUMENTS
    spec = read_json(directory / "transport.json")
    Path(spec["executable"]).write_text("changed launcher")
    with pytest.raises(ValueError, match="transport differs"):
        verify(directory)


def test_success_retains_exact_streams_and_final_without_extra_calls(tmp_path, monkeypatch):
    directory = prepared(tmp_path)
    calls = fake_process(monkeypatch)
    outcome = run_next(directory, availability_confirmed=True)
    assert outcome["state"] == "returned-valid" and len(calls) == 1
    raw = read_json(directory / "transport-results" / (outcome["id"] + ".json"))
    assert base64.b64decode(raw["stdout_base64"]) == raw["stdout"].encode()
    assert base64.b64decode(raw["stderr_base64"]) == b"Exact stderr, including CRLF.\r\n"
    assert raw["thread_ids"] == ["test-thread"]
    assert raw["final_text"] == raw["events"][-2]["item"]["text"]
    assert raw["last_message_terminator"] == "LF"
    assert raw["returncode"] == 0 and raw["requested_settings"]["model_reasoning_effort"] == "max"
    assert not Path(raw["cwd"]).exists()
    _, _, requests = verify(directory)
    assert calls[0][1]["input"] == render_prompt(requests[0]["messages"]).encode()
    assert collect(directory)[3]["counts"]["returned-valid"] == 1


@pytest.mark.parametrize("mode", ["invalid-json", "tool"])
def test_invalid_outputs_are_retained_without_repair_or_retry(tmp_path, monkeypatch, mode):
    directory = prepared(tmp_path)
    calls = fake_process(monkeypatch, mode)
    outcome = run_next(directory, availability_confirmed=True)
    assert outcome["state"] == "returned-invalid"
    assert len(calls) == 1 and collect(directory)[3]["attempts"] == 1
    assert not collect(directory)[3]["scorable"]
    raw = read_json(directory / "transport-results" / (outcome["id"] + ".json"))
    if mode == "tool":
        assert raw["tools_invoked"] is True


@pytest.mark.parametrize(
    "mode",
    [
        "process",
        "provider",
        "combined",
        "timeout",
        "launch",
        "mismatch",
        "missing-file",
        "missing-event",
    ],
)
def test_failure_pauses_without_retry_and_resolution_uses_next_request(tmp_path, monkeypatch, mode):
    directory = prepared(tmp_path)
    calls = fake_process(monkeypatch, mode)
    with pytest.raises(RuntimeError, match="external resolution"):
        run_study(directory, availability_confirmed=True)
    assert len(calls) == 1
    first = verify(directory)[2][0]["id"]
    assert collect(directory)[3]["counts"]["provider-error"] == 1
    raw_path = directory / "transport-results" / (first + ".json")
    preserved = raw_path.read_bytes()
    raw = read_json(raw_path)
    if mode in ("mismatch", "missing-file", "missing-event"):
        assert raw["isError"] is True and raw["error"] == raw["output_validation_error"]
        assert base64.b64decode(raw["stdout_base64"]) == raw["stdout"].encode()
        assert base64.b64decode(raw["stderr_base64"]) == b"Exact stderr, including CRLF.\r\n"
        if mode == "missing-file":
            assert raw["last_message_file_base64"] is None
        else:
            assert raw["last_message_file_base64"] is not None
    with pytest.raises(ValueError, match="external resolution"):
        run_next(directory, availability_confirmed=True)
    assert len(calls) == 1
    resolve_failure(directory, first, "Synthetic test resolution; no actual model called.")
    next_calls = fake_process(monkeypatch)
    second = run_next(directory, availability_confirmed=True)
    assert len(next_calls) == 1 and second["id"] == verify(directory)[2][1]["id"]
    assert second["id"] != first
    assert raw_path.read_bytes() == preserved


def test_bridge_requires_luna_and_does_not_overwrite_outputs(tmp_path, monkeypatch):
    directory = prepared(tmp_path)
    calls = fake_process(monkeypatch)
    identity = verify(directory)[2][0]["id"]
    raw_path = directory / "transport-results" / (identity + ".json")
    raw_path.parent.mkdir()
    raw_path.symlink_to(directory / "fixture.json")
    fixture_bytes = (directory / "fixture.json").read_bytes()
    with pytest.raises(ValueError, match="overwrite"):
        run_next(directory, availability_confirmed=True)
    assert len(calls) == 0 and collect(directory)[3]["attempts"] == 0
    assert (directory / "fixture.json").read_bytes() == fixture_bytes
    qwen = tmp_path / "qwen"
    prepare(qwen, FIXTURE, POLICY)
    with pytest.raises(ValueError, match="luna-max"):
        run_next(qwen, availability_confirmed=True)
    assert not calls
