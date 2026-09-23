from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import types

import pytest

ROOT = Path(__file__).parents[1]
PKG = ROOT / "experiments" / "mkm_secure_agent_runtime_v0"
sys.path.insert(0, str(PKG))

from approval import ApprovalBroker  # noqa: E402
from ollama_manager import OllamaManager, OllamaManagerError, _validate_loopback_url  # noqa: E402
from tray_controller import TrayController  # noqa: E402


@pytest.fixture()
def controller(tmp_path: Path):
    approved = tmp_path / "approved"
    approved.mkdir()
    state = tmp_path / "state"
    broker = ApprovalBroker(state, protected_roots=[approved])
    ollama = OllamaManager("http://127.0.0.1:11434")
    return TrayController(broker, ollama), broker, approved, state


def test_ollama_url_is_fail_closed():
    assert _validate_loopback_url("http://127.0.0.1:11434") == "http://127.0.0.1:11434"
    assert _validate_loopback_url("http://localhost:11434") == "http://localhost:11434"
    with pytest.raises(OllamaManagerError):
        _validate_loopback_url("http://192.168.1.10:11434")
    with pytest.raises(OllamaManagerError):
        _validate_loopback_url("https://127.0.0.1:11434")
    with pytest.raises(OllamaManagerError):
        _validate_loopback_url("http://127.0.0.1:9999")


def test_controller_lists_only_pending_unexpired(controller):
    ctl, broker, approved, _ = controller
    a = broker.request(
        action="write_text",
        target=str(approved / "a.txt"),
        args_sha256="a" * 64,
        ttl_seconds=600,
    )
    b = broker.request(
        action="run_command",
        target=str(approved),
        args_sha256="b" * 64,
        ttl_seconds=600,
    )
    broker.approve(b["approval_id"])

    rows = ctl.pending()
    assert [x.approval_id for x in rows] == [a["approval_id"]]


def test_poll_notifies_each_new_pending_once(controller):
    seen = []
    ctl, broker, approved, _ = controller
    ctl.on_new_approval = lambda item: seen.append(item.approval_id)

    req = broker.request(
        action="write_text",
        target=str(approved / "x.txt"),
        args_sha256="c" * 64,
        ttl_seconds=600,
    )
    ctl.poll()
    ctl.poll()
    assert seen == [req["approval_id"]]


def test_controller_approve_and_deny_are_local_broker_actions(controller):
    ctl, broker, approved, _ = controller
    one = broker.request(
        action="write_text",
        target=str(approved / "x.txt"),
        args_sha256="d" * 64,
        ttl_seconds=600,
    )
    two = broker.request(
        action="run_command",
        target=str(approved),
        args_sha256="e" * 64,
        ttl_seconds=600,
    )

    assert ctl.approve(one["approval_id"])["status"] == "APPROVED"
    assert ctl.deny(two["approval_id"])["status"] == "DENIED"


def test_pending_ignores_expired_record(controller):
    ctl, broker, approved, _ = controller
    req = broker.request(
        action="write_text",
        target=str(approved / "x.txt"),
        args_sha256="f" * 64,
        ttl_seconds=600,
    )
    path = broker._path(req["approval_id"])
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["expires_at"] = (
        datetime.now(timezone.utc) - timedelta(seconds=10)
    ).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    broker._atomic_write(path, payload)
    assert ctl.pending() == []


def test_ensure_running_forces_loopback_env(monkeypatch, tmp_path: Path):
    fake_exe = tmp_path / "ollama.exe"
    fake_exe.write_bytes(b"x")
    manager = OllamaManager("http://127.0.0.1:11434")

    monkeypatch.setattr("ollama_manager.find_ollama_executable", lambda: fake_exe)
    healthy = iter([False, True, True])
    monkeypatch.setattr(manager, "is_healthy", lambda timeout=1.0: next(healthy))
    monkeypatch.setattr(manager, "status", lambda: types.SimpleNamespace(
        available=True,
        endpoint=manager.base_url,
        executable=str(fake_exe),
        started_by_runtime=True,
        pid=1234,
        model_count=0,
        detail="HEALTHY",
    ))

    captured = {}

    class FakeProc:
        pid = 1234
        returncode = None
        def poll(self): return None
        def terminate(self): self.returncode = 0
        def wait(self, timeout=None): return 0
        def kill(self): self.returncode = -9

    def fake_popen(argv, **kwargs):
        captured["argv"] = argv
        captured["env"] = kwargs["env"]
        return FakeProc()

    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    status = manager.ensure_running(wait_seconds=0.5)
    assert status.available is True
    assert captured["argv"] == [str(fake_exe), "serve"]
    assert captured["env"]["OLLAMA_HOST"] == "127.0.0.1:11434"


def test_failed_ollama_start_cleans_process(monkeypatch, tmp_path: Path):
    fake_exe = tmp_path / "ollama.exe"
    fake_exe.write_bytes(b"x")
    manager = OllamaManager("http://127.0.0.1:11434")

    monkeypatch.setattr("ollama_manager.find_ollama_executable", lambda: fake_exe)
    monkeypatch.setattr(manager, "is_healthy", lambda timeout=1.0: False)

    class FakeProc:
        pid = 777
        returncode = None
        terminated = False
        def poll(self): return self.returncode
        def terminate(self):
            self.terminated = True
            self.returncode = 0
        def wait(self, timeout=None): return self.returncode
        def kill(self):
            self.returncode = -9

    proc = FakeProc()
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: proc)
    monkeypatch.setattr("ollama_manager.time.sleep", lambda _x: None)
    ticks = iter([0.0, 1.0, 2.0, 3.0])
    monkeypatch.setattr("ollama_manager.time.monotonic", lambda: next(ticks))

    with pytest.raises(OllamaManagerError):
        manager.ensure_running(wait_seconds=0.5)
    assert proc.terminated is True


def test_tray_module_imports_when_dependencies_installed():
    import tray_app  # noqa: F401
