"""WTT pilot intake target resolver (auto tenant + session)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESOLVE = ROOT / "scripts/resolve_wtt_pilot_intake_target_v1.py"


def test_resolve_single_file_stem_tenant(tmp_path: Path, monkeypatch) -> None:
    intake = tmp_path / "intake"
    intake.mkdir()
    jsonl = intake / "acme-wtt-pilot-v1.jsonl"
    row = {
        "session_id": "x1",
        "domain_tag": "customer-support-chat",
        "labels": ["masked", "not_customer_data", "research_only"],
        "customer_provided": True,
        "turns": [{"role": "user", "text": "masked refund ███"}],
    }
    jsonl.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")

    proc = subprocess.run(
        [
            sys.executable,
            str(RESOLVE),
            "--session-jsonl",
            str(jsonl),
            "--out",
            str(tmp_path / "resolve.json"),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    report = json.loads((tmp_path / "resolve.json").read_text(encoding="utf-8"))
    assert report["tenant_id"] == "acme-wtt-pilot-v1"


def test_resolve_missing_file_exit_1(tmp_path: Path) -> None:
    proc = subprocess.run(
        [
            sys.executable,
            str(RESOLVE),
            "--session-jsonl",
            str(tmp_path / "missing.jsonl"),
            "--out",
            str(tmp_path / "resolve.json"),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
