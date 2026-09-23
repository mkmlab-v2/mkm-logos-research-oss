from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import time

import pytest
from mcp import Client

ROOT = Path(__file__).parents[1]
PKG = ROOT / "experiments" / "mkm_secure_agent_runtime_v0"
sys.path.insert(0, str(PKG))

from approval import ApprovalBroker  # noqa: E402
from app_adapters import (  # noqa: E402
    AdapterSpec,
    AppAdapterLayer,
    AppAdapterRegistry,
    CLICK_LOW_RISK,
    OBSERVE,
    SET_TEXT_CLEAN,
)
from desktop_ui import DesktopActionLayer  # noqa: E402
from developer_adapter import DeveloperWorkspaceAdapter  # noqa: E402
from mcp_server import create_server  # noqa: E402
from runtime import RuntimeConfig, SecureAgentRuntime  # noqa: E402
from ui_refs import UIRefStore  # noqa: E402


pytestmark = pytest.mark.skipif(os.name != "nt", reason="Windows UIA fixture only")


@pytest.fixture()
def editor_fixture(tmp_path: Path):
    script = tmp_path / "editor_fixture.ps1"
    script.write_text(
        r'''
Add-Type -AssemblyName System.Windows.Forms
$form = New-Object System.Windows.Forms.Form
$form.Text = "MKM Developer Adapter Fixture"
$form.Width = 560
$form.Height = 220
$label = New-Object System.Windows.Forms.Label
$label.Text = "Synthetic VS Code Surface"
$label.Left = 20
$label.Top = 30
$label.Width = 300
$form.Controls.Add($label)
[void]$form.ShowDialog()
''',
        encoding="utf-8",
    )
    proc = subprocess.Popen([
        "powershell", "-NoProfile", "-STA", "-ExecutionPolicy", "Bypass",
        "-File", str(script),
    ])
    try:
        yield proc
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()


def _registry() -> AppAdapterRegistry:
    return AppAdapterRegistry([
        AdapterSpec(
            adapter_id="editor.vscode.v0",
            display_name="Synthetic VS Code Fixture",
            process_names=("powershell.exe",),
            capabilities=(OBSERVE, CLICK_LOW_RISK, SET_TEXT_CLEAN),
            risk_class="SYNTHETIC_DEVELOPER_TEST",
            notes="Synthetic mapping only.",
        )
    ])


def _git(workspace: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=workspace,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def _workspace(tmp_path: Path, *, with_tests: bool = True) -> Path:
    workspace = tmp_path / "approved" / "repo"
    workspace.mkdir(parents=True)
    _git(workspace, "init")
    _git(workspace, "config", "user.email", "fixture@example.invalid")
    _git(workspace, "config", "user.name", "MKM Fixture")
    (workspace / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    if with_tests:
        tests = workspace / "tests"
        tests.mkdir()
        (tests / "test_smoke.py").write_text(
            "def test_fixture():\n    assert 2 + 2 == 4\n",
            encoding="utf-8",
        )
    _git(workspace, "add", ".")
    _git(workspace, "commit", "-m", "fixture baseline")
    return workspace


def _build(tmp_path: Path, workspace: Path):
    approved = tmp_path / "approved"
    state = tmp_path / "state"
    runtime = SecureAgentRuntime(RuntimeConfig(
        approved_roots=[approved],
        audit_log=state / "audit" / "actions.jsonl",
    ))
    broker = ApprovalBroker(state, protected_roots=[approved])
    refs = UIRefStore(state, ttl_seconds=180)
    desktop = DesktopActionLayer(refs)
    app = AppAdapterLayer(desktop, refs, registry=_registry())
    developer = DeveloperWorkspaceAdapter(runtime.config, app)
    server = create_server(
        runtime,
        broker,
        desktop_layer=desktop,
        app_layer=app,
        developer_layer=developer,
    )
    return runtime, broker, refs, desktop, app, developer, server


def _find_window(desktop: DesktopActionLayer, pid: int):
    deadline = time.time() + 8
    while time.time() < deadline:
        rows = desktop.list_windows(max_windows=100)
        hits = [r for r in rows if r["summary"]["process_id"] == pid]
        if hits:
            return hits[0]
        time.sleep(0.2)
    raise AssertionError("editor fixture window not found")


@pytest.mark.anyio
async def test_dev_status_is_read_only_and_bound_to_editor(tmp_path: Path, editor_fixture):
    workspace = _workspace(tmp_path)
    _, _, _, desktop, _, _, server = _build(tmp_path, workspace)
    win = _find_window(desktop, editor_fixture.pid)
    (workspace / "app.py").write_text("VALUE = 2\n", encoding="utf-8")

    async with Client(server) as client:
        result = await client.call_tool(
            "dev_workspace_status",
            {"window_ref": win["ui_ref"], "workspace_path": str(workspace)},
        )
    body = result.structured_content
    assert body["adapter_id"] == "editor.vscode.v0"
    assert body["binding_state"] == "REQUEST_SCOPED_PAIR_ASSOCIATION_NOT_ESTABLISHED"
    assert body["git"]["entry_count"] >= 1
    assert any(x["path"] == "app.py" for x in body["git"]["entries"])
    assert body["send_gate"] == "HOLD"


@pytest.mark.anyio
async def test_dev_diff_releases_clean_patch(tmp_path: Path, editor_fixture):
    workspace = _workspace(tmp_path)
    _, _, _, desktop, _, _, server = _build(tmp_path, workspace)
    win = _find_window(desktop, editor_fixture.pid)
    (workspace / "app.py").write_text("VALUE = 3\n", encoding="utf-8")

    async with Client(server) as client:
        result = await client.call_tool(
            "dev_git_diff",
            {"window_ref": win["ui_ref"], "workspace_path": str(workspace)},
        )
    diff = result.structured_content["diff"]
    assert diff["blocked"] is False
    assert "VALUE = 3" in diff["text"]
    assert result.structured_content["send_gate"] == "HOLD"


@pytest.mark.anyio
async def test_dev_diff_blocks_secret_like_patch(tmp_path: Path, editor_fixture):
    workspace = _workspace(tmp_path)
    _, _, _, desktop, _, _, server = _build(tmp_path, workspace)
    win = _find_window(desktop, editor_fixture.pid)
    (workspace / "app.py").write_text(
        "password=supersecretvalue\n",
        encoding="utf-8",
    )

    async with Client(server) as client:
        result = await client.call_tool(
            "dev_git_diff",
            {"window_ref": win["ui_ref"], "workspace_path": str(workspace)},
        )
    diff = result.structured_content["diff"]
    assert diff["blocked"] is True
    assert diff["text"] is None
    assert diff["privacy_state"] == "SECRET"
    assert len(diff["sha256"]) == 64


@pytest.mark.anyio
async def test_detect_pytest_profile_is_fixed(tmp_path: Path, editor_fixture):
    workspace = _workspace(tmp_path)
    _, _, _, desktop, _, _, server = _build(tmp_path, workspace)
    win = _find_window(desktop, editor_fixture.pid)

    async with Client(server) as client:
        result = await client.call_tool(
            "dev_detect_tests",
            {"window_ref": win["ui_ref"], "workspace_path": str(workspace)},
        )
    profile = result.structured_content["profile"]
    assert result.structured_content["status"] == "CANDIDATE"
    assert profile["profile_id"] == "pytest.quiet.v0"
    assert profile["argv"] == ["python", "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider"]


@pytest.mark.anyio
async def test_request_dev_test_does_not_execute_before_approval(tmp_path: Path, editor_fixture):
    workspace = _workspace(tmp_path)
    marker = workspace / "ran.txt"
    (workspace / "tests" / "test_side_effect.py").write_text(
        "from pathlib import Path\n"
        "def test_side_effect():\n"
        "    Path('ran.txt').write_text('ran', encoding='utf-8')\n"
        "    assert True\n",
        encoding="utf-8",
    )
    _, _, _, desktop, _, _, server = _build(tmp_path, workspace)
    win = _find_window(desktop, editor_fixture.pid)

    async with Client(server) as client:
        req = await client.call_tool(
            "request_dev_test",
            {
                "window_ref": win["ui_ref"],
                "workspace_path": str(workspace),
                "profile_id": "pytest.quiet.v0",
                "timeout_seconds": 60,
            },
        )
    body = req.structured_content
    assert body["status"] == "HUMAN_GATE"
    assert body["executed"] is False
    assert body["argv"] == ["python", "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider"]
    assert not marker.exists()


@pytest.mark.anyio
async def test_approved_dev_test_executes_fixed_profile(tmp_path: Path, editor_fixture):
    workspace = _workspace(tmp_path)
    _, broker, _, desktop, _, _, server = _build(tmp_path, workspace)
    win = _find_window(desktop, editor_fixture.pid)

    async with Client(server) as client:
        req = await client.call_tool(
            "request_dev_test",
            {
                "window_ref": win["ui_ref"],
                "workspace_path": str(workspace),
                "timeout_seconds": 60,
            },
        )
        body = req.structured_content
        broker.approve(body["approval_id"])
        ex = await client.call_tool(
            "execute_dev_test",
            {
                "window_ref": win["ui_ref"],
                "workspace_path": str(workspace),
                "approval_id": body["approval_id"],
                "timeout_seconds": 60,
            },
        )
    result = ex.structured_content
    assert result["executed"] is True
    assert result["returncode"] == 0
    assert result["profile_id"] == "pytest.quiet.v0"
    assert result["output"]["stdout"]["blocked"] is False
    assert "passed" in result["output"]["stdout"]["text"]
    assert result["send_gate"] == "HOLD"
    assert not (workspace / ".pytest_cache").exists()
    assert not any(p.name == "__pycache__" for p in workspace.rglob("__pycache__"))


@pytest.mark.anyio
async def test_dev_test_approval_is_exact_timeout_bound(tmp_path: Path, editor_fixture):
    workspace = _workspace(tmp_path)
    _, broker, _, desktop, _, _, server = _build(tmp_path, workspace)
    win = _find_window(desktop, editor_fixture.pid)

    async with Client(server) as client:
        req = await client.call_tool(
            "request_dev_test",
            {
                "window_ref": win["ui_ref"],
                "workspace_path": str(workspace),
                "timeout_seconds": 60,
            },
        )
        body = req.structured_content
        broker.approve(body["approval_id"])
        ex = await client.call_tool(
            "execute_dev_test",
            {
                "window_ref": win["ui_ref"],
                "workspace_path": str(workspace),
                "approval_id": body["approval_id"],
                "timeout_seconds": 61,
            },
        )
    assert ex.is_error is True


@pytest.mark.anyio
async def test_unknown_test_profile_is_rejected(tmp_path: Path, editor_fixture):
    workspace = _workspace(tmp_path)
    _, _, _, desktop, _, _, server = _build(tmp_path, workspace)
    win = _find_window(desktop, editor_fixture.pid)

    async with Client(server) as client:
        result = await client.call_tool(
            "request_dev_test",
            {
                "window_ref": win["ui_ref"],
                "workspace_path": str(workspace),
                "profile_id": "arbitrary.command.v1",
            },
        )
    assert result.is_error is True


@pytest.mark.anyio
async def test_workspace_outside_approved_root_is_rejected(tmp_path: Path, editor_fixture):
    workspace = _workspace(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    _, _, _, desktop, _, _, server = _build(tmp_path, workspace)
    win = _find_window(desktop, editor_fixture.pid)

    async with Client(server) as client:
        result = await client.call_tool(
            "dev_workspace_status",
            {"window_ref": win["ui_ref"], "workspace_path": str(outside)},
        )
    assert result.is_error is True


def test_no_pytest_marker_keeps_profile_not_established(tmp_path: Path, editor_fixture):
    workspace = _workspace(tmp_path, with_tests=False)
    _, _, _, desktop, _, developer, _ = _build(tmp_path, workspace)
    win = _find_window(desktop, editor_fixture.pid)
    result = developer.detect_test_profile(win["ui_ref"], workspace)
    assert result["status"] == "NOT_ESTABLISHED"
    assert result["profile"] is None
