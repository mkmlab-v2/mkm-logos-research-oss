from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "record_logos_s1_shadow_promotion_human_approval_v1.py"


def test_records_when_kpi_ready(tmp_path: Path) -> None:
    kpi = tmp_path / "kpi.json"
    out = tmp_path / "approval.json"
    log = tmp_path / "approval.jsonl"

    kpi.write_text(
        json.dumps(
            {
                "schema": "logos_shadow_promotion_kpi_progress_v1",
                "status": "READY_FOR_REVIEW",
                "passed": True,
                "checks": {"all": True},
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--kpi-progress-json",
            str(kpi),
            "--output-json",
            str(out),
            "--approval-log-jsonl",
            str(log),
            "--skip-agent-decision-log",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "logos_s1_shadow_promotion_human_approval_v1"
    assert doc.get("decision") == "ACK_NEXT_STAGE_PLANNING"
    assert log.is_file()
    assert log.read_text(encoding="utf-8").strip()


def test_exits_when_kpi_not_ready(tmp_path: Path) -> None:
    kpi = tmp_path / "kpi_bad.json"
    out = tmp_path / "approval.json"
    kpi.write_text(
        json.dumps({"status": "IN_PROGRESS", "passed": False}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--kpi-progress-json",
            str(kpi),
            "--output-json",
            str(out),
            "--skip-agent-decision-log",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode != 0
