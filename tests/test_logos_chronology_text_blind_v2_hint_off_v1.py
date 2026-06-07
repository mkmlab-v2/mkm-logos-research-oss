from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AB = ROOT / "scripts/run_logos_chronology_text_blind_v2_hint_off_ab_v1.py"
OUT = ROOT / "reports/logos_chronology_text_blind_v2_hint_off_ab_v1_latest.json"


def test_hint_off_ab_runs_and_measures_uplift() -> None:
    rc = subprocess.call([sys.executable, str(AB), "--skip-v2-rerun"], cwd=str(ROOT))
    assert rc == 0
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    cmp_ = doc["compare"]
    assert doc["commander_approved"] is True
    assert cmp_["train_holdout_hit_at_1_full"] is not None
    assert cmp_["train_holdout_hit_at_1_no_hints"] is not None
    # era hints should not reduce strict hit@1 vs full v2 on aggregate
    assert float(cmp_["all_events_hit_at_1_no_hints"]) <= float(cmp_["all_events_hit_at_1_full"]) + 1e-9
