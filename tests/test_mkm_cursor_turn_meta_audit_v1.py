# Keywords: turn_meta, audit, suspect_first, sparse_log

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "scripts/check_mkm_cursor_turn_meta_audit_v1.py"


def test_audit_empty_log_warns_not_fails(tmp_path: Path):
    log = tmp_path / "empty.jsonl"
    out = tmp_path / "audit.json"
    proc = subprocess.run(
        [sys.executable, str(AUDIT), "--log", str(log), "--out", str(out)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["status"] == "WARN"
    assert any(w.startswith("sparse_log:") for w in doc["warnings"])


def test_audit_self_audit_row_passes(tmp_path: Path):
    log = tmp_path / "turn_meta.jsonl"
    row = {
        "schema": "mkm_cursor_turn_meta_v1",
        "continuity_id": "audit-smoke",
        "self_audit": {"suspect_first": True, "violation_flags": []},
        "required_ssot_missing": [],
    }
    log.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
    out = tmp_path / "audit.json"
    proc = subprocess.run(
        [sys.executable, str(AUDIT), "--log", str(log), "--out", str(out)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["status"] in ("PASS", "WARN")
    assert doc["suspect_first_true_count"] == 1


def test_cursorrules_template_has_suspect_first():
    text = (ROOT / "docs/final/artifacts/cursorrules_slim_ssot_v1.txt").read_text(encoding="utf-8")
    assert "Suspect-first" in text
    assert "mkm_cursor_turn_meta_log.jsonl" in text
