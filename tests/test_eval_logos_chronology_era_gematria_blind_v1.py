from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/eval_logos_chronology_era_gematria_blind_v1.py"


def test_eval_logos_chronology_era_gematria_blind_v1_runs() -> None:
    out = ROOT / "reports/tmp_gematria_era_blind_eval_test.json"
    insights = ROOT / "reports/tmp_gematria_era_insights_test.json"
    if out.is_file():
        out.unlink()
    if insights.is_file():
        insights.unlink()
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--output-json",
            str(out),
            "--insights-json",
            str(insights),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr or cp.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_chronology_era_gematria_blind_eval_v1"
    assert doc["hypothesis_tier"] == "[HYPO]"
    tb = doc["evaluations"]["text_blind_gematria"]["summary"]
    assert tb["n_events"] == 47
    assert tb["hit_at_1_strict"] is not None
