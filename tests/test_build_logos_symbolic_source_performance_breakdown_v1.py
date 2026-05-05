from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_logos_symbolic_source_performance_breakdown_v1.py"


def test_build_source_performance_breakdown_smoke(tmp_path: Path) -> None:
    backtest = tmp_path / "bt.json"
    backtest.write_text(
        json.dumps(
            {
                "rows": [
                    {"source_id": "label_guided_seed", "dataset_partition": "train_holdout", "predicted_direction": "up", "hit": 1},
                    {"source_id": "label_guided_seed", "dataset_partition": "locked_eval", "predicted_direction": "down", "hit": 1},
                    {"source_id": "external_macro_signals", "dataset_partition": "train_holdout", "predicted_direction": "up", "hit": 0},
                ]
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "out.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--backtest-json",
            str(backtest),
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stdout + cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("summary", {}).get("n_sources") == 2
    by_source = {r["source_id"]: r for r in doc.get("source_performance", [])}
    assert by_source["label_guided_seed"]["hit_rate"] == 1.0
    assert by_source["external_macro_signals"]["hit_rate"] == 0.0

