# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.5, K:0.2, M:0.2}
# Balance: 92
# Purpose: Smoke test for eval_prophecy_shadow_panel_v1.py
# Keywords: pytest, prophecy, shadow, panel
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _write_csv(path: Path, closes: list[float], start: str = "2026-01-01") -> None:
    from datetime import date, timedelta

    d0 = date.fromisoformat(start)
    lines = ["Date,Open,High,Low,Close,Volume"]
    for i, c in enumerate(closes):
        ds = (d0 + timedelta(days=i)).isoformat()
        lines.append(f"{ds},{c},{c},{c},{c},1000")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_shadow_panel_eval_with_synthetic_inputs(tmp_path: Path) -> None:
    ws = Path(__file__).resolve().parents[1]
    kcsv = tmp_path / "k.csv"
    bcsv = tmp_path / "b.csv"
    # Prior map keys by eval_date row use (close[t-1]-close[t-2])/close[t-2] for that eval_date.
    # Put the big move on (t-2 -> t-1) so both legs can clear thresholds with small drift on day t.
    _write_csv(kcsv, [100.0, 100.1, 100.2, 100.3, 100.4, 103.0, 103.1])
    _write_csv(bcsv, [200.0, 200.1, 200.2, 200.3, 200.4, 250.0, 251.0])

    score = {
        "schema": "btrack_prophecy_score_v1",
        "rows": [
            {
                "instrument": "kospi",
                "eval_date": "2026-01-07",
                "predicted_direction": "bear",
                "actual_direction": "bull",
            },
            {
                "instrument": "btc",
                "eval_date": "2026-01-07",
                "predicted_direction": "bear",
                "actual_direction": "bull",
            },
        ],
    }
    score_path = tmp_path / "score.json"
    score_path.write_text(json.dumps(score), encoding="utf-8")

    combo = {
        "schema": "prophecy_instrument_combo_sweep_v1",
        "best_candidate": {"kospi_mode": "bull", "btc": {"low_thr": 0.1, "high_thr": 0.2}},
    }
    combo_path = tmp_path / "combo.json"
    combo_path.write_text(json.dumps(combo), encoding="utf-8")

    holdout = {
        "schema": "prophecy_per_date_combo_holdout_v1",
        "best_params_from_train": {
            "dz_self": 0.0,
            "dz_cross": 0.01,
            "w_self": -0.5,
            "w_cross": 1.0,
            "kospi_bull_bias": 1.0,
            "up_thr": 0.5,
            "down_thr": -0.5,
        },
    }
    hold_path = tmp_path / "holdout.json"
    hold_path.write_text(json.dumps(holdout), encoding="utf-8")

    out = tmp_path / "shadow_out.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(ws / "scripts" / "eval_prophecy_shadow_panel_v1.py"),
            "--score-json",
            str(score_path),
            "--kospi-csv",
            str(kcsv),
            "--btc-csv",
            str(bcsv),
            "--combo-sweep-json",
            str(combo_path),
            "--holdout-json",
            str(hold_path),
            "--shadow-mode",
            "both",
            "--output",
            str(out),
        ],
        cwd=str(ws),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "prophecy_shadow_panel_eval_v1"
    lanes = doc.get("lanes")
    assert isinstance(lanes, list) and len(lanes) == 2
    for lane in lanes:
        m = lane.get("metrics_all")
        assert isinstance(m, dict)
        assert m.get("n_evaluated") == 2
        assert m.get("price_hits") == 2


def test_shadow_panel_eval_stdout_only_smoke() -> None:
    ws = Path(__file__).resolve().parents[1]
    proc = subprocess.run(
        [
            sys.executable,
            str(ws / "scripts" / "eval_prophecy_shadow_panel_v1.py"),
            "--stdout-only",
            "--shadow-mode",
            "instrument_combo_best",
        ],
        cwd=str(ws),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    doc = json.loads(proc.stdout)
    assert doc.get("schema") == "prophecy_shadow_panel_eval_v1"
    assert isinstance(doc.get("lanes"), list) and doc["lanes"]
