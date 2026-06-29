"""WTT intake drop watch — eligibility without live intake."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WATCH = ROOT / "scripts/watch_wtt_pilot_intake_drop_v1.py"


def _row(sid: str) -> dict:
    return {
        "session_id": sid,
        "domain_tag": "customer-support-chat",
        "labels": ["masked", "not_customer_data", "research_only"],
        "customer_provided": True,
        "turns": [{"role": "user", "text": "masked ███ refund"}],
    }


def test_drop_watch_dry_run_eligible(tmp_path: Path) -> None:
    intake = tmp_path / "intake"
    intake.mkdir()
    jsonl = intake / "acme-wtt-pilot-v1.jsonl"
    lines = [_row(f"s{i:03d}") for i in range(20)]
    jsonl.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in lines) + "\n", encoding="utf-8")

    out = tmp_path / "report.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(WATCH),
            "--state",
            str(tmp_path / "state.json"),
            "--out",
            str(out),
            "--intake-dir",
            str(intake),
            "--dry-run",
            "--force-jsonl",
            str(jsonl),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["actions"][0]["action"] == "would_run_intake"


def test_drop_watch_skips_fill_template(tmp_path: Path) -> None:
    intake = tmp_path / "intake"
    intake.mkdir()
    jsonl = intake / "acme-wtt-pilot-v1.jsonl"
    row = _row("t1")
    row["labels"] = ["masked", "pilot_fill_template", "research_only"]
    row["customer_provided"] = False
    lines = [row] * 20
    jsonl.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in lines) + "\n", encoding="utf-8")

    out = tmp_path / "report.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(WATCH),
            "--state",
            str(tmp_path / "state.json"),
            "--out",
            str(out),
            "--intake-dir",
            str(intake),
            "--dry-run",
            "--force-jsonl",
            str(jsonl),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["actions"][0]["action"] == "skip"
    assert report["actions"][0]["reason"] == "not_eligible"
