from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD_GOLD = ROOT / "scripts/build_logos_chronology_off_fixture_era_gold_v1.py"
RUN_AB = ROOT / "scripts/run_logos_chronology_off_fixture_text_blind_v2_ab_v1.py"
GOLD = ROOT / "docs/final/artifacts/logos_chronology_off_fixture_era_gold_v1_latest.json"
HIST = ROOT / "docs/final/artifacts/fixtures/logos_chronology_historical_era_gold_v1.json"
OUT_AB = ROOT / "reports/logos_chronology_off_fixture_text_blind_v2_ab_v1_latest.json"
OUT_HOLD = ROOT / "reports/logos_chronology_off_fixture_holdout_v1_latest.json"


def test_off_fixture_gold_disjoint_from_historical() -> None:
    rc = subprocess.call([sys.executable, str(BUILD_GOLD), "--max-expansion-rows", "5"], cwd=str(ROOT))
    assert rc == 0
    doc = json.loads(GOLD.read_text(encoding="utf-8"))
    hist = json.loads(HIST.read_text(encoding="utf-8"))
    hist_ids = {e["event_id"] for e in hist["events"]}
    off_ids = {e["event_id"] for e in doc["events"]}
    assert hist_ids.isdisjoint(off_ids)
    assert doc["cohort_definition"]["disjoint_from_historical_gold"] is True
    assert doc["n_events"] >= 27


def test_off_fixture_text_blind_v2_ab_measured() -> None:
    assert GOLD.is_file(), "run gold build test first or build gold manually"
    rc = subprocess.call(
        [sys.executable, str(RUN_AB), "--skip-gold-build", "--max-expansion-rows", "5"],
        cwd=str(ROOT),
    )
    assert rc == 0
    ab = json.loads(OUT_AB.read_text(encoding="utf-8"))
    hold = json.loads(OUT_HOLD.read_text(encoding="utf-8"))
    assert ab["compare"]["off_fixture_measured"] is True
    assert ab["compare"]["target_met"] is True
    assert hold["cohort"] == "off_fixture"
    v1 = float(ab["compare"]["all_events_hit_at_1_v1"])
    v2 = float(ab["compare"]["all_events_hit_at_1_v2"])
    assert v2 >= 0.15
    assert ab["compare"]["target_met"] is True
