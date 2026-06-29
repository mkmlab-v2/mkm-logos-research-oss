"""WTT dialog risk policy tune round 2 — overload FN reduction."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TUNE = ROOT / "scripts/tune_wtt_dialog_risk_policy_from_corpus_v1.py"
CORPUS = ROOT / "data/wtt/examples/wtt_spicy_masked_sessions_v1.example.jsonl"


def test_tune_round2_improves_overload_misses(tmp_path: Path) -> None:
    if not CORPUS.is_file():
        subprocess.run(
            [sys.executable, "scripts/build_wtt_spicy_masked_sessions_v1.py"],
            cwd=str(ROOT),
            check=True,
        )
    out = tmp_path / "tune_r2.json"
    proc = subprocess.run(
        [sys.executable, str(TUNE), "--jsonl", str(CORPUS), "--round", "2", "--out", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["tune_round"] == 2
    assert report["candidate"]["hit_rate"] >= report["baseline"]["hit_rate"]
    assert report["candidate"]["miss_by_type"].get("overload", 99) <= report["baseline"]["miss_by_type"].get(
        "overload", 0
    )
