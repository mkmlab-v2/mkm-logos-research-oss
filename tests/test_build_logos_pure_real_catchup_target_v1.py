import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_logos_pure_real_catchup_target_v1.py"


def test_build_logos_pure_real_catchup_target_smoke(tmp_path: Path) -> None:
    status_json = tmp_path / "status.json"
    table_json = tmp_path / "table.json"
    out_json = tmp_path / "out.json"

    status_json.write_text(
        json.dumps(
            {
                "schema": "logos_pure_real_daily_execution_status_v1",
                "today_utc": "2026-05-05",
                "status": "OFF_TRACK_NEED_CATCHUP",
                "plan_today": {"deficit_vs_plan": 2},
            }
        ),
        encoding="utf-8",
    )
    table_json.write_text(
        json.dumps(
            {
                "schema": "logos_pure_real_7day_execution_table_v1",
                "daily_targets": {
                    "source_rows_per_day": 4,
                    "source_days_per_day": 4,
                    "new_unique_days_per_day": 2,
                },
            }
        ),
        encoding="utf-8",
    )

    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--status-json",
            str(status_json),
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
    assert doc.get("schema") == "logos_pure_real_catchup_target_v1"
    assert doc.get("action") == "CATCH_UP_TODAY"
    tgt = doc.get("today_catchup_target") or {}
    assert int(tgt.get("recommended_extra_rows_today", 0)) == 2
    assert int(tgt.get("recommended_total_rows_today", 0)) == 6

