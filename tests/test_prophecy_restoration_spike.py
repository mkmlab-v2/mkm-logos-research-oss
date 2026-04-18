# @MKM12-METADATA
# Type: Logic
# Purpose: Smoke — run_prophecy_restoration_spike.py baseline vs overlay delta.
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "scripts" / "run_prophecy_restoration_spike.py"


def test_prophecy_restoration_spike_delta_on_stress_year(tmp_path: Path) -> None:
    """Bear→neutral in stress years changes at least one outcome vs fixed actuals."""
    ym = tmp_path / "years.json"
    ym.write_text(
        json.dumps(
            {
                "schema": "btrack_4d_to_ohaeng_regime_year_map_sample_v1",
                "rows": [{"regime_id": "lehman", "start_year": 2008, "end_year": 2009}],
            }
        ),
        encoding="utf-8",
    )
    score = tmp_path / "score.json"
    score.write_text(
        json.dumps(
            {
                "schema": "btrack_prophecy_score_v1",
                "rows": [
                    {
                        "eval_date": "2008-09-15",
                        "instrument": "kospi",
                        "predicted_direction": "bear",
                        "actual_direction": "neutral",
                    },
                    {
                        "eval_date": "2026-04-01",
                        "instrument": "kospi",
                        "predicted_direction": "bear",
                        "actual_direction": "bull",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    cp = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--score-json",
            str(score),
            "--year-map-json",
            str(ym),
            "--overlay",
            "stress_bear_to_neutral_v0",
            "--stdout-only",
        ],
        capture_output=True,
        text=True,
        cwd=str(_ROOT),
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(cp.stdout)
    assert doc.get("schema") == "prophecy_overlay_ablation_spike_v1"
    assert doc.get("research_only") is True
    assert doc.get("after_overlay", {}).get("overlay_rows_modified") == 1
    assert doc.get("delta_hit_rate") is not None
    assert doc.get("delta_hit_rate") != 0.0


def test_prophecy_restoration_spike_script_exists() -> None:
    assert _SCRIPT.is_file(), str(_SCRIPT)


def test_prior_day_shock_overlay_changes_hit_rate(tmp_path: Path) -> None:
    """prior-day return <= threshold triggers bear→neutral using only CSV history."""
    csv_path = tmp_path / "kospi.csv"
    csv_path.write_text(
        "\n".join(
            [
                "Date,Open,High,Low,Close,Volume",
                "2026-03-03,100,101,99,98,1000",
                "2026-03-04,98,99,93,94,1000",
                "2026-03-05,94,96,93,96,1000",
            ]
        ),
        encoding="utf-8",
    )
    ym = tmp_path / "years.json"
    ym.write_text(json.dumps({"schema": "dummy", "rows": []}), encoding="utf-8")
    score = tmp_path / "score.json"
    score.write_text(
        json.dumps(
            {
                "schema": "btrack_prophecy_score_v1",
                "rows": [
                    {
                        "eval_date": "2026-03-05",
                        "instrument": "kospi",
                        "predicted_direction": "bear",
                        "actual_direction": "neutral",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    cp = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--score-json",
            str(score),
            "--year-map-json",
            str(ym),
            "--kospi-csv",
            str(csv_path),
            "--prior-return-threshold",
            "-0.02",
            "--overlay",
            "prior_day_shock_bear_abstain_v0",
            "--stdout-only",
        ],
        capture_output=True,
        text=True,
        cwd=str(_ROOT),
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(cp.stdout)
    assert doc.get("after_overlay", {}).get("overlay_rows_modified") == 1
    assert doc.get("baseline", {}).get("price_directional_hit_rate") == 0.0
    assert doc.get("after_overlay", {}).get("price_directional_hit_rate") == 1.0
    assert doc.get("delta_hit_rate") == 1.0
