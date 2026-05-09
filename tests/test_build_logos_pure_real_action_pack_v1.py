import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_logos_pure_real_action_pack_v1.py"


def test_build_logos_pure_real_action_pack_smoke(tmp_path: Path) -> None:
    progress_json = tmp_path / "progress.json"
    min_intake_json = tmp_path / "min.json"
    status_json = tmp_path / "status.json"
    catchup_json = tmp_path / "catchup.json"
    out_json = tmp_path / "out.json"

    progress_json.write_text(
        json.dumps(
            {
                "schema": "logos_pure_real_progress_report_v1",
                "checkpoint": {"current_unique_days": 21, "target_unique_days": 30, "gap_unique_days": 9},
            }
        ),
        encoding="utf-8",
    )
    min_intake_json.write_text(
        json.dumps(
            {
                "schema": "logos_pure_real_minimum_intake_plan_v1",
                "recommended_daily_minimum": {"required_new_source_rows_per_day": 4},
            }
        ),
        encoding="utf-8",
    )
    status_json.write_text(
        json.dumps(
            {
                "schema": "logos_pure_real_daily_execution_status_v1",
                "today_utc": "2026-05-05",
                "status": "OFF_TRACK_NEED_CATCHUP",
            }
        ),
        encoding="utf-8",
    )
    catchup_json.write_text(
        json.dumps(
            {
                "schema": "logos_pure_real_catchup_target_v1",
                "status_ref": {"deficit_vs_plan": 2},
                "today_catchup_target": {"recommended_total_rows_today": 6},
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
            str(min_intake_json),
            "--status-json",
            str(status_json),
            "--catchup-json",
            str(catchup_json),
            "--output-json",
            str(out_json),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout

    doc = json.loads(out_json.read_text(encoding="utf-8"))
    assert doc.get("schema") == "logos_pure_real_action_pack_v1"
    assert (doc.get("status") or {}).get("priority") == "EXECUTE_CATCHUP_TODAY"
    assert int((doc.get("today_targets") or {}).get("recommended_total_rows_today", 0)) == 6

