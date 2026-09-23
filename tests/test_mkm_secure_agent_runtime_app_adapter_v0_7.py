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
    AppAdapterError,
    AppAdapterLayer,
    AppAdapterRegistry,
    CLICK_LOW_RISK,
    OBSERVE,
    SET_TEXT_CLEAN,
)
from desktop_ui import DesktopActionLayer  # noqa: E402
from mcp_server import create_server  # noqa: E402
from runtime import RuntimeConfig, SecureAgentRuntime  # noqa: E402
from ui_refs import UIRefStore  # noqa: E402


pytestmark = pytest.mark.skipif(os.name != "nt", reason="Windows UIA only")


@pytest.fixture()
def app_fixture(tmp_path: Path):
    sentinel = tmp_path / "clicked.txt"
    script = tmp_path / "fixture.ps1"
    script.write_text(
        r'''
Add-Type -AssemblyName System.Windows.Forms
$form = New-Object System.Windows.Forms.Form
$form.Text = "MKM App Adapter Synthetic Fixture"
$form.Width = 620
$form.Height = 300

$text = New-Object System.Windows.Forms.TextBox
$text.Name = "InputBox"
$text.Left = 20
$text.Top = 25
$text.Width = 400
$form.Controls.Add($text)

$safe = New-Object System.Windows.Forms.Button
$safe.Name = "SafeButton"
$safe.Text = "Safe Action"
$safe.Left = 20
$safe.Top = 80
$safe.Width = 130
$safe.Add_Click({ Set-Content -Encoding UTF8 -Path "SENTINEL_PATH" -Value "clicked" })
$form.Controls.Add($safe)

$danger = New-Object System.Windows.Forms.Button
$danger.Name = "DeleteButton"
$danger.Text = "Delete All"
$danger.Left = 170
$danger.Top = 80
$danger.Width = 130
$form.Controls.Add($danger)

[void]$form.ShowDialog()
'''.replace("SENTINEL_PATH", sentinel.as_posix()),
        encoding="utf-8",
    )
    proc = subprocess.Popen([
        "powershell", "-NoProfile", "-STA", "-ExecutionPolicy", "Bypass",
        "-File", str(script),
    ])
    try:
        yield proc, sentinel
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()


def _build(tmp_path: Path, *, registry: AppAdapterRegistry | None = None):
    approved = tmp_path / "approved"
    approved.mkdir(exist_ok=True)
    state = tmp_path / "state"
    runtime = SecureAgentRuntime(RuntimeConfig(
        approved_roots=[approved],
        audit_log=state / "audit" / "actions.jsonl",
    ))
    broker = ApprovalBroker(state, protected_roots=[approved])
    refs = UIRefStore(state, ttl_seconds=180)
    desktop = DesktopActionLayer(refs)
    app = AppAdapterLayer(desktop, refs, registry=registry)
    server = create_server(runtime, broker, desktop_layer=desktop, app_layer=app)
    return runtime, broker, refs, desktop, app, server


def _synthetic_registry() -> AppAdapterRegistry:
    return AppAdapterRegistry([
        AdapterSpec(
            adapter_id="fixture.winforms.v0",
            display_name="Synthetic WinForms Fixture",
            process_names=("powershell.exe",),
            capabilities=(OBSERVE, CLICK_LOW_RISK, SET_TEXT_CLEAN),
            risk_class="SYNTHETIC_TEST_ONLY",
            notes="Fixture only.",
        )
    ])


def _find_window(desktop: DesktopActionLayer, pid: int):
    deadline = time.time() + 8
    while time.time() < deadline:
        rows = desktop.list_windows(max_windows=100)
        hits = [r for r in rows if r["summary"]["process_id"] == pid]
        if hits:
            return hits[0]
        time.sleep(0.2)
    raise AssertionError("fixture window not found")


def _control_by_label(rows, label: str):
    for row in rows:
        if (row["summary"].get("name") or {}).get("text") == label:
            return row
    raise AssertionError(f"control not found: {label}")


def _edit(rows):
    for row in rows:
        if row["summary"].get("control_type") == "Edit":
            return row
    raise AssertionError("Edit control not found")


def test_builtin_browser_is_observe_only():
    registry = AppAdapterRegistry()
    match = registry.identify_summary({
        "process_name": "chrome.exe",
        "class_name": "Chrome_WidgetWin_1",
    })
    assert match.adapter_id == "browser.chromium.observe.v0"
    assert match.capabilities == (OBSERVE,)


def test_unmatched_is_observe_only():
    registry = AppAdapterRegistry()
    match = registry.identify_summary({
        "process_name": "unknown-app.exe",
        "class_name": "UnknownClass",
    })
    assert match.matched is False
    assert match.capabilities == (OBSERVE,)
    assert match.risk_class == "OBSERVE_ONLY_UNMATCHED"


def test_ambiguous_adapter_match_fails_closed():
    registry = AppAdapterRegistry([
        AdapterSpec(
            adapter_id="one",
            display_name="One",
            process_names=("same.exe",),
        ),
        AdapterSpec(
            adapter_id="two",
            display_name="Two",
            process_names=("same.exe",),
        ),
    ])
    with pytest.raises(AppAdapterError, match="ambiguous"):
        registry.identify_summary({
            "process_name": "same.exe",
            "class_name": "X",
        })


@pytest.mark.anyio
async def test_app_identify_and_inspect_synthetic_fixture(tmp_path: Path, app_fixture):
    proc, _ = app_fixture
    _, _, _, desktop, _, server = _build(
        tmp_path, registry=_synthetic_registry()
    )
    win = _find_window(desktop, proc.pid)
    async with Client(server) as client:
        ident = await client.call_tool(
            "app_identify_window", {"window_ref": win["ui_ref"]}
        )
        inspected = await client.call_tool(
            "app_inspect_window",
            {"window_ref": win["ui_ref"], "max_controls": 100},
        )
    assert ident.structured_content["adapter"]["adapter_id"] == "fixture.winforms.v0"
    assert CLICK_LOW_RISK in ident.structured_content["adapter"]["capabilities"]
    assert inspected.structured_content["control_count"] > 0
    assert inspected.structured_content["send_gate"] == "HOLD"


@pytest.mark.anyio
async def test_legacy_ui_mutation_is_denied_when_adapter_layer_active(tmp_path: Path, app_fixture):
    proc, _ = app_fixture
    _, _, _, desktop, app, server = _build(
        tmp_path, registry=_synthetic_registry()
    )
    win = _find_window(desktop, proc.pid)
    controls = app.inspect_window(win["ui_ref"])["controls"]
    safe = _control_by_label(controls, "Safe Action")

    async with Client(server) as client:
        result = await client.call_tool(
            "request_ui_click", {"control_ref": safe["ui_ref"]}
        )
    body = result.structured_content
    assert body["status"] == "DENIED"
    assert body["reason"] == "APP_ADAPTER_REQUIRED"
    assert body["executed"] is False


@pytest.mark.anyio
async def test_adapter_safe_click_requires_approval_and_has_effect(tmp_path: Path, app_fixture):
    proc, sentinel = app_fixture
    _, broker, _, desktop, app, server = _build(
        tmp_path, registry=_synthetic_registry()
    )
    win = _find_window(desktop, proc.pid)
    safe = _control_by_label(
        app.inspect_window(win["ui_ref"])["controls"], "Safe Action"
    )

    async with Client(server) as client:
        req = await client.call_tool(
            "request_app_click",
            {"window_ref": win["ui_ref"], "control_ref": safe["ui_ref"]},
        )
        body = req.structured_content
        assert body["status"] == "HUMAN_GATE"
        assert body["adapter_id"] == "fixture.winforms.v0"
        assert not sentinel.exists()

        broker.approve(body["approval_id"])
        ex = await client.call_tool(
            "execute_app_click",
            {
                "window_ref": win["ui_ref"],
                "control_ref": safe["ui_ref"],
                "approval_id": body["approval_id"],
            },
        )
    assert ex.structured_content["executed"] is True
    assert ex.structured_content["adapter_id"] == "fixture.winforms.v0"

    deadline = time.time() + 3
    while time.time() < deadline and not sentinel.exists():
        time.sleep(0.1)
    assert sentinel.exists()


@pytest.mark.anyio
async def test_adapter_still_denies_high_risk_control(tmp_path: Path, app_fixture):
    proc, _ = app_fixture
    _, _, _, desktop, app, server = _build(
        tmp_path, registry=_synthetic_registry()
    )
    win = _find_window(desktop, proc.pid)
    danger = _control_by_label(
        app.inspect_window(win["ui_ref"])["controls"], "Delete All"
    )

    async with Client(server) as client:
        result = await client.call_tool(
            "request_app_click",
            {"window_ref": win["ui_ref"], "control_ref": danger["ui_ref"]},
        )
    body = result.structured_content
    assert body["status"] == "DENIED"
    assert body["reason"] == "HIGH_RISK_CONTROL_LABEL"
    assert body["executed"] is False


@pytest.mark.anyio
async def test_adapter_clean_edit_text_round_trip(tmp_path: Path, app_fixture):
    proc, _ = app_fixture
    _, broker, _, desktop, app, server = _build(
        tmp_path, registry=_synthetic_registry()
    )
    win = _find_window(desktop, proc.pid)
    edit = _edit(app.inspect_window(win["ui_ref"])["controls"])

    async with Client(server) as client:
        req = await client.call_tool(
            "request_app_set_text",
            {
                "window_ref": win["ui_ref"],
                "control_ref": edit["ui_ref"],
                "text": "adapter-fixture",
            },
        )
        body = req.structured_content
        assert body["status"] == "HUMAN_GATE"
        broker.approve(body["approval_id"])
        ex = await client.call_tool(
            "execute_app_set_text",
            {
                "window_ref": win["ui_ref"],
                "control_ref": edit["ui_ref"],
                "text": "adapter-fixture",
                "approval_id": body["approval_id"],
            },
        )
    assert ex.structured_content["executed"] is True
    assert desktop.get_value_for_test(edit["ui_ref"]) == "adapter-fixture"


@pytest.mark.anyio
async def test_adapter_denies_personal_text(tmp_path: Path, app_fixture):
    proc, _ = app_fixture
    _, _, _, desktop, app, server = _build(
        tmp_path, registry=_synthetic_registry()
    )
    win = _find_window(desktop, proc.pid)
    edit = _edit(app.inspect_window(win["ui_ref"])["controls"])

    async with Client(server) as client:
        result = await client.call_tool(
            "request_app_set_text",
            {
                "window_ref": win["ui_ref"],
                "control_ref": edit["ui_ref"],
                "text": "user@example.com",
            },
        )
    body = result.structured_content
    assert body["status"] == "DENIED"
    assert body["reason"] == "TEXT_PRIVACY_PERSONAL"


def test_control_from_different_window_ref_is_denied(tmp_path: Path):
    approved = tmp_path / "approved"
    approved.mkdir()
    state = tmp_path / "state"
    refs = UIRefStore(state)
    runtime = SecureAgentRuntime(RuntimeConfig(
        approved_roots=[approved],
        audit_log=state / "audit.jsonl",
    ))
    desktop = DesktopActionLayer(refs)
    registry = _synthetic_registry()
    app = AppAdapterLayer(desktop, refs, registry=registry)

    win = refs.issue(
        kind="window",
        selector={"top_handle": 1, "process_id": 100},
        summary={"process_name": "powershell.exe", "class_name": "Fixture"},
    )
    ctl = refs.issue(
        kind="control",
        selector={"top_handle": 2, "process_id": 100},
        summary={"control_type": "Button", "name": {"text": "Safe Action"}},
    )
    policy = app.app_policy(win["ui_ref"], ctl["ui_ref"], action="click")
    assert policy["decision"] == "DENY"
    assert "does not belong" in policy["reason"]
