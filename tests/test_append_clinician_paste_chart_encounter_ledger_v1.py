"""pytest: clinician paste chart encounter ledger append."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
FIXTURE = ROOT / "projects/no1kmedi/scripts/fixtures/paste-chart-encounter-ledger-sample-v1.json"


def test_append_ledger_from_fixture(tmp_path: Path) -> None:
    ledger = tmp_path / "paste_chart_encounter_ledger_v1.jsonl"
    out = tmp_path / "append_report.json"
    proc = subprocess.run(
        [
            PY,
            "scripts/append_clinician_paste_chart_encounter_ledger_v1.py",
            "--ledger",
            str(ledger),
            "--from-json",
            str(FIXTURE),
            "--output",
            str(out),
            "--source",
            "pytest",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    lines = ledger.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["schema"] == "clinician_paste_chart_encounter_ledger_v1"
    assert row["hypothesis_tier"] == "B"
    assert row["human_gold_required"] is True
    assert row["pipeline_summary"]["stages_ok"] >= 4
    assert row["encounter_ref"]["display_label_redacted"].startswith("김")


def test_accumulation_chain_offline_smoke_only(tmp_path: Path) -> None:
    out = tmp_path / "chain.json"
    proc = subprocess.run(
        [
            PY,
            "scripts/run_clinician_encounter_accumulation_chain_v1.py",
            "--skip-ledger-append",
            "--skip-registry-rebuild",
            "--output",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=180,
    )
    assert proc.returncode == 0, proc.stderr[-800:] if proc.stderr else proc.stdout
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["ok"] is True
