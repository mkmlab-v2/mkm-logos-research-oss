import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_logos_pure_real_daily_execution_status_v1.py"


def test_build_logos_pure_real_daily_execution_status_smoke(tmp_path: Path) -> None:
    progress_json = tmp_path / "progress.json"
    table_json = tmp_path / "table.json"
    out_json = tmp_path / "out.json"
    today = datetime.now(timezone.utc).date().isoformat()

    progress_json.write_text(
        json.dumps(
            {
                "schema": "logos_pure_real_progress_report_v1",
                "checkpoint": {"target_unique_days": 30, "current_unique_days": 21, "gap_unique_days": 9},
            }
        ),
        encoding="utf-8",
    )
    table_json.write_text(
        json.dumps(
            {
                "schema": "logos_pure_real_7day_execution_table_v1",
                "execution_table": [
                    {
                        "day_label": "D+0",
                        "date_utc": today,
                        "planned_new_unique_days": 2,
                        "cumulative_target_unique_days": 23,
                    }
                ],
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
            "--table-json",
            str(table_json),
            "--output-json",
            str(out_json),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(out_json.read_text(encoding="utf-8"))
    assert doc.get("schema") == "logos_pure_real_daily_execution_status_v1"
    assert doc.get("status") == "OFF_TRACK_NEED_CATCHUP"
    assert int((doc.get("plan_today") or {}).get("deficit_vs_plan", 0)) == 2

