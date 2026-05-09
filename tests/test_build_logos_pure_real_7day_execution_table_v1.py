import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_logos_pure_real_7day_execution_table_v1.py"


def test_build_logos_pure_real_7day_execution_table_smoke(tmp_path: Path) -> None:
    progress_json = tmp_path / "progress.json"
    intake_json = tmp_path / "intake.json"
    out_json = tmp_path / "out.json"

    progress_json.write_text(
        json.dumps(
            {
                "schema": "logos_pure_real_progress_report_v1",
                "checkpoint": {
                    "target_unique_days": 30,
                    "current_unique_days": 21,
                    "gap_unique_days": 9,
                    "required_new_unique_days_per_day": 2,
                },
            }
        ),
        encoding="utf-8",
    )
    intake_json.write_text(
        json.dumps(
            {
                "schema": "logos_pure_real_minimum_intake_plan_v1",
                "recommended_daily_minimum": {
                    "required_new_unique_days_per_day": 2,
                    "required_new_source_days_per_day": 4,
                    "required_new_source_rows_per_day": 4,
                },
            }
        ),
        encoding="utf-8",
    )

    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--progress-json",
            str(progress_json),
            "--minimum-intake-json",
            str(intake_json),
            "--output-json",
            str(out_json),
            "--days",
            "7",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout

    doc = json.loads(out_json.read_text(encoding="utf-8"))
    assert doc.get("schema") == "logos_pure_real_7day_execution_table_v1"
    assert int((doc.get("daily_targets") or {}).get("source_rows_per_day", 0)) == 4
    rows = doc.get("execution_table") or []
    assert len(rows) == 7
    assert int(rows[0].get("planned_new_unique_days", 0)) == 2
    assert int(rows[4].get("planned_new_unique_days", 0)) == 1
    assert int(rows[5].get("planned_new_unique_days", 0)) == 0

