"""Tests for wrong-direction counterfactual matrix builder."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_counterfactual_matrix_smoke(tmp_path: Path) -> None:
    wrong = ["2026-04-02"]
    base_pd = tmp_path / "per_date_baseline.json"
    var_pd = tmp_path / "per_date_blend035.json"
    for path, pred in [(base_pd, "bull"), (var_pd, "bear")]:
        path.write_text(
            json.dumps(
                {
                    "rows": [
                        {
                            "eval_date": "2026-04-02",
                            "instrument": "btc",
                            "predicted_direction": pred,
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
    sweep = {
        "wrong_dir_dates": wrong,
        "variants": [
            {"slug": "baseline", "per_date_path": str(base_pd)},
            {"slug": "blend035", "per_date_path": str(var_pd)},
        ],
    }
    sweep_path = tmp_path / "sweep.json"
    out_path = tmp_path / "out.json"
    sweep_path.write_text(json.dumps(sweep), encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/build_btrack_wrong_dir_counterfactual_matrix_v1.py",
            "--sweep-json",
            str(sweep_path),
            "--output",
            str(out_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out_path.read_text(encoding="utf-8"))
    assert doc["variant_summary"][0]["n_would_fix_wrong_dir"] == 1
    assert doc["matrix_rows"][0]["cells"]["blend035"]["would_fix_wrong_dir"] is True
