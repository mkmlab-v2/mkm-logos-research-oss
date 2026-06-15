"""Week 2 fuel layer audits — NL mapping · lexicon smoke · hub triangle."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(script: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def test_notebooklm_lane_mapping_audit_exit_ok() -> None:
    proc = _run("check_notebooklm_lane_mapping_audit_v1.py")
    assert proc.returncode == 0, proc.stderr + proc.stdout
    out = ROOT / "reports/notebooklm_lane_mapping_audit_v1_latest.json"
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "notebooklm_lane_mapping_audit_v1"
    assert doc["ok"] is True
    assert doc["blocking_violation_count"] == 0


def test_notebooklm_lane_mapping_strict_known_groups_exit_ok() -> None:
    proc = _run("check_notebooklm_lane_mapping_audit_v1.py", "--strict-known-groups")
    assert proc.returncode == 0, proc.stderr + proc.stdout
    doc = json.loads((ROOT / "reports/notebooklm_lane_mapping_audit_v1_latest.json").read_text(encoding="utf-8"))
    assert doc["ok"] is True
    assert doc["blocking_violation_count"] == 0
    # Documented ops notebook share (OPS_COMMAND_ANCHOR + LTM_GRAPH_OPS) may appear when maps align to portfolio.


def test_lexicon_lookup_smoke_exit_ok() -> None:
    proc = _run("check_lexicon_lookup_smoke_v1.py")
    assert proc.returncode == 0, proc.stderr + proc.stdout
    doc = json.loads((ROOT / "reports/lexicon_lookup_smoke_v1_latest.json").read_text(encoding="utf-8"))
    assert doc["ok"] is True
    assert doc["hit_count"] > 0
    assert doc["chat_injection"] is False


def test_hub_developer_copy_triangle_exit_ok() -> None:
    proc = _run("check_hub_developer_copy_triangle_v1.py")
    assert proc.returncode == 0, proc.stderr + proc.stdout
    doc = json.loads((ROOT / "reports/hub_developer_copy_triangle_v1_latest.json").read_text(encoding="utf-8"))
    assert doc["ok"] is True
    ids = {c["id"] for c in doc["checks"] if c.get("ok")}
    assert "plugins_apply" in ids
    assert "plugins_benchmark" in ids
    assert "plugins_reproduce" in ids
    assert "dev_page_apply" in ids
