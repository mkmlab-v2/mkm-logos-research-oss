import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_logos_pure_real_minimum_intake_plan_v1.py"


def test_build_logos_pure_real_minimum_intake_plan_smoke(tmp_path: Path) -> None:
    meta_json = tmp_path / "meta.json"
    plan_json = tmp_path / "plan.json"
    out_json = tmp_path / "out.json"

    meta_json.write_text(
        json.dumps(
            {
                "schema": "news_observation_non_synthetic_backfill_meta_v1",
                "output_non_synthetic_unique_days": 21,
            }
        ),
        encoding="utf-8",
    )
    plan_json.write_text(
        json.dumps(
            {
                "schema": "logos_pure_real_day30_execution_plan_v1",
                "checkpoint": {"target_unique_days": 30},
                "daily_collection_options": [{"plan_days": 3}, {"plan_days": 5}, {"plan_days": 7}],
            }
        ),
        encoding="utf-8",
    )

    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--meta-json",
            str(meta_json),
            "--plan-json",
            str(plan_json),
            "--output-json",
            str(out_json),
            "--remaining-days",
            "5",
            "--rows-per-source-day",
            "2",
            "--unique-day-yield-per-source-day",
            "0.8",
            "--safety-buffer-ratio",
            "1.25",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout

    doc = json.loads(out_json.read_text(encoding="utf-8"))
    assert doc.get("schema") == "logos_pure_real_minimum_intake_plan_v1"
    assert int((doc.get("checkpoint") or {}).get("gap_unique_days", 0)) == 9
    rec = doc.get("recommended_daily_minimum") or {}
    assert int(rec.get("required_new_unique_days_per_day", 0)) == 2
    assert int(rec.get("required_new_source_days_per_day_base", 0)) == 3
    assert int(rec.get("required_new_source_days_per_day", 0)) == 4
    assert int(rec.get("required_new_source_rows_per_day", 0)) == 8
    assert len(doc.get("minimum_intake_by_horizon") or []) >= 3

