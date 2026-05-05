from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "fast_promotion_gate_v1.py"


def test_fast_promotion_gate_v1_smoke(tmp_path: Path) -> None:
    promotion = {
        "combined_all_passed": True,
    }
    hit = {
        "metrics": {
            "price_directional_hit_rate": 0.6,
            "n_evaluated": 10,
        }
    }
    ext = {"mode": "latest_ok", "degraded": False}
    score = {
        "rows": [{"instrument": "kospi", "eval_date": "2026-04-29"}],
    }
    pg_path = tmp_path / "pg.json"
    hr_path = tmp_path / "hr.json"
    ex_path = tmp_path / "ext.json"
    sc_path = tmp_path / "score.json"
    out_path = tmp_path / "out.json"
    for path, doc in (
        (pg_path, promotion),
        (hr_path, hit),
        (ex_path, ext),
        (sc_path, score),
    ):
        path.write_text(json.dumps(doc), encoding="utf-8")

    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--promotion-gates",
            str(pg_path),
            "--hit-rate",
            str(hr_path),
            "--external-status",
            str(ex_path),
            "--score",
            str(sc_path),
            "--output",
            str(out_path),
            "--min-hit-rate",
            "0.5",
            "--min-n",
            "5",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(out_path.read_text(encoding="utf-8"))
    assert doc["schema"] == "fast_promotion_gate_v1"
    assert doc["result"]["live_ready"] is True
    assert doc["result"]["recommendation"] == "live_candidate"


def test_script_exists() -> None:
    assert SCRIPT.is_file()
