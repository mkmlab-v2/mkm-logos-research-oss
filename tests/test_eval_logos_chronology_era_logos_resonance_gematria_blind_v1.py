from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/eval_logos_chronology_era_logos_resonance_gematria_blind_v1.py"


def test_eval_logos_chronology_era_logos_resonance_gematria_blind_v1_runs() -> None:
    out = ROOT / "reports/tmp_logos_resonance_gematria_era_blind_eval_test.json"
    insights = ROOT / "reports/tmp_logos_resonance_gematria_era_insights_test.json"
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
    assert doc["schema"] == "logos_chronology_era_logos_resonance_gematria_blind_eval_v1"
    assert doc["hypothesis_tier"] == "[HYPO]"
    sm = doc["evaluation"]["summary"]
    assert sm["n_events"] == 47
    assert sm["hit_at_1_strict"] is not None
    assert doc["inputs"]["n_corpus_verses_encoded"] <= 256
