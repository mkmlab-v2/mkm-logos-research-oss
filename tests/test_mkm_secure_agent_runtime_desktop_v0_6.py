from __future__ import annotations

import asyncio
import hashlib
import json
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
from desktop_ui import DesktopActionLayer, DesktopUIError  # noqa: E402
from mcp_server import _digest, create_server  # noqa: E402
from runtime import RuntimeConfig, SecureAgentRuntime  # noqa: E402
from ui_refs import UIRefStore, UIRefError  # noqa: E402


pytestmark = pytest.mark.skipif(os.name != "nt", reason="Windows UIA only")


@pytest.fixture()
def uia_fixture(tmp_path: Path):
    sentinel = tmp_path / "clicked.txt"
    script = tmp_path / "fixture.ps1"
    script.write_text(
        r'''
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$form = New-Object System.Windows.Forms.Form
$form.Text = "MKM UIA Synthetic Fixture"
$form.Name = "MKMFixtureForm"
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
'''.replace("SENTINEL_PATH", str(sentinel).replace("\\", "\\\\")),
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


def _build(tmp_path: Path):
    approved = tmp_path / "approved"
    approved.mkdir(exist_ok=True)
    state = tmp_path / "state"
    runtime = SecureAgentRuntime(RuntimeConfig(
        approved_roots=[approved],
        audit_log=state / "audit" / "actions.jsonl",
    ))
    broker = ApprovalBroker(state, protected_roots=[approved])
    refs = UIRefStore(state, ttl_seconds=180)
    layer = DesktopActionLayer(refs)
    server = create_server(runtime, broker, desktop_layer=layer)
    return runtime, broker, refs, layer, server


def _find_fixture_window(layer: DesktopActionLayer, pid: int):
    deadline = time.time() + 8
    while time.time() < deadline:
        rows = layer.list_windows(max_windows=100)
        hits = [r for r in rows if r["summary"]["process_id"] == pid]
        if hits:
            return hits[0]
        time.sleep(0.2)
    raise AssertionError("fixture window not found")


def _controls(layer: DesktopActionLayer, window_ref: str):
    result = layer.inspect_window(window_ref, max_controls=100)
    return result["controls"]


def _control_by_label(rows, label: str):
    for row in rows:
        name = row["summary"].get("name") or {}
        if name.get("text") == label:
            return row
    raise AssertionError(f"control label not found: {label}")


def _edit_control(rows):
    for row in rows:
        if row["summary"].get("control_type") == "Edit":
            return row
    raise AssertionError("Edit control not found")


def test_window_title_hidden_by_default(tmp_path: Path, uia_fixture):
    proc, _ = uia_fixture
    _, _, _, layer, _ = _build(tmp_path)
    win = _find_fixture_window(layer, proc.pid)
    title = win["summary"]["title"]
    assert title["text"] == "[WINDOW_TITLE_HIDDEN]"
    assert title["sensitive"] is True
    assert len(title["sha256"]) == 64


def test_inspect_hides_edit_content_but_shows_action_labels(tmp_path: Path, uia_fixture):
    proc, _ = uia_fixture
    _, _, _, layer, _ = _build(tmp_path)
    win = _find_fixture_window(layer, proc.pid)
    rows = _controls(layer, win["ui_ref"])
    assert _control_by_label(rows, "Safe Action")
    assert _control_by_label(rows, "Delete All")
    edit = _edit_control(rows)
    assert edit["summary"]["name"]["text"] == "[EDIT_CONTENT_HIDDEN]"


def test_policy_allows_safe_click_gate_and_denies_delete(tmp_path: Path, uia_fixture):
    proc, _ = uia_fixture
    _, _, _, layer, _ = _build(tmp_path)
    win = _find_fixture_window(layer, proc.pid)
    rows = _controls(layer, win["ui_ref"])
    safe = _control_by_label(rows, "Safe Action")
    danger = _control_by_label(rows, "Delete All")
    assert layer.action_policy(safe["ui_ref"], action="click")["decision"] == "HUMAN_GATE"
    denied = layer.action_policy(danger["ui_ref"], action="click")
    assert denied["decision"] == "DENY"
    assert denied["reason"] == "HIGH_RISK_CONTROL_LABEL"


def test_set_text_denies_personal_and_allows_clean_text(tmp_path: Path, uia_fixture):
    proc, _ = uia_fixture
    _, _, _, layer, _ = _build(tmp_path)
    win = _find_fixture_window(layer, proc.pid)
    edit = _edit_control(_controls(layer, win["ui_ref"]))
    assert layer.action_policy(edit["ui_ref"], action="set_text", text="fixture-value")["decision"] == "HUMAN_GATE"
    denied = layer.action_policy(edit["ui_ref"], action="set_text", text="user@example.com")
    assert denied["decision"] == "DENY"
    assert denied["reason"] == "TEXT_PRIVACY_PERSONAL"


@pytest.mark.anyio
async def test_mcp_click_requires_local_approval_then_executes(tmp_path: Path, uia_fixture):
    proc, sentinel = uia_fixture
    _, broker, _, layer, server = _build(tmp_path)
    win = _find_fixture_window(layer, proc.pid)
    safe = _control_by_label(_controls(layer, win["ui_ref"]), "Safe Action")

    async with Client(server) as client:
        req = await client.call_tool("request_ui_click", {"control_ref": safe["ui_ref"]})
        body = req.structured_content
        assert body["status"] == "HUMAN_GATE"
        assert body["executed"] is False
        assert not sentinel.exists()

        broker.approve(body["approval_id"])
        ex = await client.call_tool(
            "execute_ui_click",
            {"control_ref": safe["ui_ref"], "approval_id": body["approval_id"]},
        )
        assert ex.structured_content["executed"] is True

    deadline = time.time() + 3
    while time.time() < deadline and not sentinel.exists():
        time.sleep(0.1)
    assert sentinel.exists()


@pytest.mark.anyio
async def test_mcp_high_risk_click_request_is_blocked(tmp_path: Path, uia_fixture):
    proc, _ = uia_fixture
    _, _, _, layer, server = _build(tmp_path)
    win = _find_fixture_window(layer, proc.pid)
    danger = _control_by_label(_controls(layer, win["ui_ref"]), "Delete All")

    async with Client(server) as client:
        result = await client.call_tool(
            "request_ui_click", {"control_ref": danger["ui_ref"]}
        )
    assert result.is_error is True


@pytest.mark.anyio
async def test_mcp_set_text_round_trip_and_exact_approval(tmp_path: Path, uia_fixture):
    proc, _ = uia_fixture
    _, broker, _, layer, server = _build(tmp_path)
    win = _find_fixture_window(layer, proc.pid)
    edit = _edit_control(_controls(layer, win["ui_ref"]))

    async with Client(server) as client:
        req = await client.call_tool(
            "request_ui_set_text",
            {"control_ref": edit["ui_ref"], "text": "fixture-value"},
        )
        body = req.structured_content
        assert body["status"] == "HUMAN_GATE"
        broker.approve(body["approval_id"])
        ex = await client.call_tool(
            "execute_ui_set_text",
            {
                "control_ref": edit["ui_ref"],
                "text": "fixture-value",
                "approval_id": body["approval_id"],
            },
        )
        assert ex.structured_content["executed"] is True
        assert ex.structured_content["text_length"] == len("fixture-value")

    resolved = layer.resolve_control(edit["ui_ref"])
    assert resolved.wrapper.get_value() == "fixture-value"


def test_ui_refs_are_ephemeral_local_records(tmp_path: Path):
    state = tmp_path / "state"
    store = UIRefStore(state, ttl_seconds=30)
    ref = store.issue(
        kind="control",
        selector={"x": 1},
        summary={"name": {"text": "Safe Action"}},
    )
    payload = store.resolve(ref["ui_ref"], expected_kind="control")
    assert payload["selector"]["x"] == 1
    assert (state / "ui_refs" / f"{ref['ui_ref']}.json").is_file()
