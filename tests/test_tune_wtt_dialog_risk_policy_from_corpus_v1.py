"""WTT dialog risk policy tune from corpus."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TUNE = ROOT / "scripts/tune_wtt_dialog_risk_policy_from_corpus_v1.py"
CORPUS = ROOT / "data/wtt/examples/wtt_spicy_masked_sessions_v1.example.jsonl"


def test_tune_improves_or_reports(tmp_path: Path) -> None:
    if not CORPUS.is_file():
        subprocess.run(
            [sys.executable, "scripts/build_wtt_spicy_masked_sessions_v1.py"],
            cwd=str(ROOT),
            check=True,
        )
    out = tmp_path / "tune.json"
    proc = subprocess.run(
        [sys.executable, str(TUNE), "--jsonl", str(CORPUS), "--out", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    report = json.loads(out.read_text(encoding="utf-8"))
    assert "baseline" in report
    assert "candidate" in report
    baseline_hr = report["baseline"]["hit_rate"]
    candidate_hr = report["candidate"]["hit_rate"]
    assert candidate_hr >= baseline_hr or baseline_hr >= 0.85
    assert (ROOT / "docs/final/artifacts/warmth_trigger_dialog_risk_policy_v1_tuned_candidate.json").is_file()
