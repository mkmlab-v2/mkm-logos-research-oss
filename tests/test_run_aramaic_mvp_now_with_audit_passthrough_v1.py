"""Contract: run_aramaic_mvp_now_with_audit.ps1 forwards switches and writes audit row."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
AUDIT_PS1 = ROOT / "scripts" / "run_aramaic_mvp_now_with_audit.ps1"


def _powershell() -> list[str]:
    for exe in ("powershell.exe", "powershell", "pwsh.exe", "pwsh"):
        p = shutil.which(exe)
        if p:
            return [p, "-NoProfile", "-ExecutionPolicy", "Bypass"]
    pytest.skip("PowerShell not found on PATH")


def _write_stub_chain(scripts_dir: Path) -> None:
    stub = r"""param(
    [switch]$SkipLogosInsightBundle
)
$ErrorActionPreference = "Stop"
$probeDir = Join-Path (Split-Path $PSScriptRoot -Parent) "_chain_probe"
New-Item -ItemType Directory -Force -Path $probeDir | Out-Null
$log = Join-Path $probeDir "invocation.json"
$o = @{ SkipLogosInsightBundlePresent = [bool]$SkipLogosInsightBundle }
[System.IO.File]::WriteAllText($log, ($o | ConvertTo-Json -Compress -Depth 4), [System.Text.UTF8Encoding]::new($false))
exit 0
"""
    scripts_dir.mkdir(parents=True, exist_ok=True)
    (scripts_dir / "run_aramaic_mvp_chain_v1.ps1").write_text(stub, encoding="utf-8")


def _write_min_score(artifacts_dir: Path) -> None:
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    doc = {
        "shift_score": 0.42,
        "conflict_ratio": 0.09,
        "insight_cap_bucket": "mid",
    }
    (artifacts_dir / "aramaic_regime_shift_score_latest.json").write_text(
        json.dumps(doc, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def test_skip_logos_insight_bundle_passthrough_to_chain(tmp_path: Path) -> None:
    ws = tmp_path / "fixture"
    (ws / "scripts").mkdir(parents=True)
    _write_stub_chain(ws / "scripts")
    _write_min_score(ws / "docs" / "final" / "artifacts")
    (ws / "reports" / "ops").mkdir(parents=True, exist_ok=True)
    audit_rel = "reports/ops/audit_passthrough_test.jsonl"
    audit_path = ws / audit_rel
    probe = ws / "_chain_probe" / "invocation.json"

    cmd = _powershell() + [
        "-File",
        str(AUDIT_PS1),
        "-WorkspaceRoot",
        str(ws),
        "-AuditLogJsonl",
        audit_rel,
        "-SkipLogosInsightBundle",
    ]
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert probe.is_file(), proc.stdout + proc.stderr
    inv = json.loads(probe.read_text(encoding="utf-8"))
    assert inv.get("SkipLogosInsightBundlePresent") is True


def test_no_skip_switch_absent_on_chain(tmp_path: Path) -> None:
    ws = tmp_path / "fixture2"
    (ws / "scripts").mkdir(parents=True)
    _write_stub_chain(ws / "scripts")
    _write_min_score(ws / "docs" / "final" / "artifacts")
    (ws / "reports" / "ops").mkdir(parents=True, exist_ok=True)
    audit_rel = "reports/ops/audit_nopass.jsonl"
    probe = ws / "_chain_probe" / "invocation.json"

    cmd = _powershell() + [
        "-File",
        str(AUDIT_PS1),
        "-WorkspaceRoot",
        str(ws),
        "-AuditLogJsonl",
        audit_rel,
    ]
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    inv = json.loads(probe.read_text(encoding="utf-8"))
    assert inv.get("SkipLogosInsightBundlePresent") is False


def test_no_webhook_sets_audit_row_flag(tmp_path: Path) -> None:
    ws = tmp_path / "fixture3"
    (ws / "scripts").mkdir(parents=True)
    _write_stub_chain(ws / "scripts")
    _write_min_score(ws / "docs" / "final" / "artifacts")
    (ws / "reports" / "ops").mkdir(parents=True, exist_ok=True)
    audit_rel = "reports/ops/audit_webhook.jsonl"
    audit_path = ws / audit_rel

    cmd = _powershell() + [
        "-File",
        str(AUDIT_PS1),
        "-WorkspaceRoot",
        str(ws),
        "-AuditLogJsonl",
        audit_rel,
        "-NoWebhook",
    ]
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    lines = [ln for ln in audit_path.read_text(encoding="utf-8-sig").splitlines() if ln.strip()]
    assert lines, "audit log should have one line"
    row = json.loads(lines[-1])
    assert row.get("webhook_disabled") is True
