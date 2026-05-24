# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.5, K:0.2, M:0.2}
# Balance: 92
# Purpose: Smoke test for instrument combo walk-forward script
# Keywords: pytest, prophecy, instrument, walkforward
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


def test_instrument_combo_walkforward_runs(tmp_path: Path) -> None:
    ws = Path(__file__).resolve().parents[1]
    kcsv = tmp_path / "k.csv"
    bcsv = tmp_path / "b.csv"
    kc = [100.0 + i * 0.1 for i in range(22)]
    bc = [200.0 + i * 0.5 for i in range(22)]
    _write_csv(kcsv, kc)
    _write_csv(bcsv, bc)
    rows: list[dict] = []
    for day in (10, 11, 12, 13, 14, 15):
        ed = f"2026-01-{day:02d}"
        rows.append(
            {"instrument": "kospi", "eval_date": ed, "predicted_direction": "bull", "actual_direction": "bull"},
        )
        rows.append({"instrument": "btc", "eval_date": ed, "predicted_direction": "bull", "actual_direction": "bull"})
    score_path = tmp_path / "score.json"
    score_path.write_text(
        json.dumps(
            {
                "inputs": {"btc_csv": str(bcsv)},
                "rows": rows,
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "inst_wf.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(ws / "scripts" / "run_prophecy_instrument_combo_walkforward_v1.py"),
            "--score-json",
            str(score_path),
            "--kospi-csv",
            str(kcsv),
            "--btc-csv",
            str(bcsv),
            "--threshold-grid=-0.01,0.00,0.01",
            "--n-folds",
            "3",
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
    assert doc.get("schema") == "prophecy_instrument_combo_walkforward_v1"
    assert isinstance(doc.get("folds"), list) and len(doc["folds"]) >= 1
    assert "mean_test_accuracy" in (doc.get("aggregate") or {})
    assert (doc.get("inputs") or {}).get("train_objective") == "beat_bull_first"


def test_instrument_combo_walkforward_accuracy_objective(tmp_path: Path) -> None:
    ws = Path(__file__).resolve().parents[1]
    kcsv = tmp_path / "k.csv"
    bcsv = tmp_path / "b.csv"
    kc = [100.0 + i * 0.1 for i in range(22)]
    bc = [200.0 + i * 0.5 for i in range(22)]
    _write_csv(kcsv, kc)
    _write_csv(bcsv, bc)
    rows: list[dict] = []
    for day in (10, 11, 12, 13, 14, 15):
        ed = f"2026-01-{day:02d}"
        rows.append(
            {"instrument": "kospi", "eval_date": ed, "predicted_direction": "bull", "actual_direction": "bull"},
        )
        rows.append({"instrument": "btc", "eval_date": ed, "predicted_direction": "bull", "actual_direction": "bull"})
    score_path = tmp_path / "score.json"
    score_path.write_text(json.dumps({"inputs": {"btc_csv": str(bcsv)}, "rows": rows}), encoding="utf-8")
    out = tmp_path / "inst_wf_acc.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(ws / "scripts" / "run_prophecy_instrument_combo_walkforward_v1.py"),
            "--score-json",
            str(score_path),
            "--kospi-csv",
            str(kcsv),
            "--btc-csv",
            str(bcsv),
            "--threshold-grid=-0.01,0.00,0.01",
            "--n-folds",
            "3",
            "--train-objective",
            "accuracy",
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
    assert (doc.get("inputs") or {}).get("train_objective") == "accuracy"
