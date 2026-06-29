from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/eval_logos_chronology_era_resonance_gematria_ensemble_blind_v1.py"


def test_eval_logos_chronology_era_resonance_gematria_ensemble_blind_v1_runs() -> None:
    out = ROOT / "reports/tmp_ensemble_era_blind_eval_test.json"
    insights = ROOT / "reports/tmp_ensemble_era_insights_test.json"
    for p in (out, insights):
        if p.is_file():
            p.unlink()
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--output-json",
            str(out),
            "--insights-json",
            str(insights),
            "--corpus-limit",
            "256",
            "--top-k",
            "4",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr or cp.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_chronology_era_resonance_gematria_ensemble_blind_eval_v1"
    assert doc["hypothesis_tier"] == "[HYPO]"
    assert len(doc["leaderboard"]) >= 7
    kw = doc["mode_evaluations"]["keyword_only"]["summary"]
    assert kw["n_events"] == 47
