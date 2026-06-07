from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUMMARIZE = ROOT / "scripts/summarize_logos_chronology_partition_holdout_v1.py"
V1 = ROOT / "docs/final/artifacts/logos_chronology_era_blind_eval_text_blind_v1_latest.json"
V2 = ROOT / "docs/final/artifacts/logos_chronology_era_blind_eval_text_blind_v2_v1_latest.json"
OUT = ROOT / "reports/logos_chronology_text_blind_v2_holdout_v1_latest.json"


def test_partition_holdout_summary_runs() -> None:
    assert V1.is_file(), "missing v1 eval artifact — run text_blind_v2 AB first"
    assert V2.is_file(), "missing v2 eval artifact — run text_blind_v2 AB first"
    rc = subprocess.call([sys.executable, str(SUMMARIZE)], cwd=str(ROOT))
    assert rc == 0
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    hold = doc["by_partition"]["train_holdout"]
    assert hold["text_blind_v1_ms_baseline"]["n"] == 20
    assert doc["compare"]["train_holdout_target_15pct_met"] is True


def test_v2_beats_v1_on_train_holdout() -> None:
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    h = doc["by_partition"]["train_holdout"]
    v1 = float(h["text_blind_v1_ms_baseline"]["hit_at_1_strict"] or 0)
    v2 = float(h["text_blind_v2_btrack_poc"]["hit_at_1_strict"] or 0)
    assert v2 > v1
    assert v2 >= 0.15
