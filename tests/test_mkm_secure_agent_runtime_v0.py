from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "experiments" / "mkm_secure_agent_runtime_v0"))

from runtime import (  # noqa: E402
    Decision,
    OllamaGateway,
    PolicyEngine,
    Privacy,
    RuntimeConfig,
    RuntimeErrorV0,
    SecretHandle,
    SecureAgentRuntime,
)


@pytest.fixture()
def runtime(tmp_path: Path) -> tuple[SecureAgentRuntime, Path]:
    root = tmp_path / "approved"
    root.mkdir()
    config = RuntimeConfig(
        approved_roots=[root],
        audit_log=tmp_path / "audit" / "actions.jsonl",
        allowed_executables=("git", "python", "python3", "pytest"),
    )
    return SecureAgentRuntime(config), root


def test_outside_root_is_fail_closed(runtime, tmp_path: Path):
    rt, _ = runtime
    outside = tmp_path / "outside.txt"
    outside.write_text("x", encoding="utf-8")
    with pytest.raises(RuntimeErrorV0, match="outside approved roots"):
        rt.read_file(outside)


def test_read_is_real_and_receipt_has_hash_not_content(runtime):
    rt, root = runtime
    p = root / "hello.txt"
    p.write_text("hello-secret-looking-text", encoding="utf-8")
    data, receipt = rt.read_file(p)
    assert data == b"hello-secret-looking-text"
    assert receipt.success is True
    log = rt.config.audit_log.read_text(encoding="utf-8")
    assert "hello-secret-looking-text" not in log
    assert receipt.result_meta["sha256"]


def test_write_requires_human_gate_and_does_not_execute(runtime):
    rt, root = runtime
    p = root / "new.txt"
    with pytest.raises(RuntimeErrorV0, match="HUMAN_GATE"):
        rt.write_file(p, b"new")
    assert not p.exists()


def test_approved_write_executes_atomically(runtime):
    rt, root = runtime
    p = root / "new.txt"
    receipt = rt.write_file(p, b"new", human_approved=True)
    assert p.read_bytes() == b"new"
    assert receipt.decision == "ALLOW"
    assert receipt.result_meta["after_sha256"]


def test_thin_coordinate_contains_sha256_without_file_body(runtime):
    rt, root = runtime
    p = root / "a.txt"
    p.write_text("coordinate me", encoding="utf-8")
    coord, _ = rt.thin_coordinate(p, domain="DEV", topic="A")
    assert coord.kind == "SOURCE"
    assert coord.domain == "DEV"
    assert coord.source_id.startswith("src:")
    assert len(coord.hash) == 64


def test_secret_handle_never_accepts_raw_value_shape():
    h = SecretHandle("secret://github/main")
    assert h.ref == "secret://github/main"
    assert "github/main" not in repr(h)
    with pytest.raises(RuntimeErrorV0):
        SecretHandle("plain-password")


def test_secret_use_never_resolves_material(runtime):
    rt, _ = runtime
    receipt = rt.use_secret_handle(
        SecretHandle("secret://github/main"),
        purpose="git-auth",
        human_approved=True,
    )
    assert receipt.result_meta["resolved"] is False
    assert receipt.result_meta["secret_material_exposed"] is False


def test_ollama_endpoint_must_be_loopback():
    OllamaGateway("http://127.0.0.1:11434")
    OllamaGateway("http://localhost:11434")
    with pytest.raises(RuntimeErrorV0, match="loopback"):
        OllamaGateway("http://192.168.0.20:11434")


def test_phi_local_model_is_hold_by_default(runtime):
    rt, _ = runtime
    assert rt.policy.decide("ollama_generate", privacy=Privacy.PHI) == Decision.HOLD


def test_secret_is_denied_to_model(runtime):
    rt, _ = runtime
    assert rt.policy.decide("ollama_generate", privacy=Privacy.SECRET) == Decision.DENY


def test_command_requires_human_gate(runtime):
    rt, root = runtime
    with pytest.raises(RuntimeErrorV0, match="HUMAN_GATE"):
        rt.run_command(["git", "status", "--short"], cwd=root)


def test_blocked_git_push_is_rejected_before_execution(runtime):
    rt, root = runtime
    with pytest.raises(RuntimeErrorV0, match="blocked"):
        rt.run_command(["git", "push"], cwd=root, human_approved=True)


def test_argv_only_read_only_git_command_can_execute(runtime):
    rt, root = runtime
    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True, text=True)
    cp, receipt = rt.run_command(
        ["git", "status", "--short"], cwd=root, human_approved=True
    )
    assert cp.returncode == 0
    assert receipt.result_meta["executed"] is True
    assert receipt.semantic_state == "NOT_ADJUDICATED"
    assert receipt.send_gate == "HOLD"


def test_unknown_action_holds(runtime):
    rt, _ = runtime
    assert rt.policy.decide("future_browser_click") == Decision.HOLD


def test_receipts_are_jsonl_and_no_semantic_pass(runtime):
    rt, root = runtime
    p = root / "x.txt"
    p.write_text("x", encoding="utf-8")
    rt.read_file(p)
    rows = [
        json.loads(line)
        for line in rt.config.audit_log.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert rows
    assert all(r["semantic_state"] == "NOT_ADJUDICATED" for r in rows)
    assert all(r["send_gate"] == "HOLD" for r in rows)
