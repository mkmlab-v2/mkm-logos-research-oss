from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AB = ROOT / "scripts/run_logos_chronology_text_blind_v2_en_headline_ab_v1.py"
OUT = ROOT / "reports/logos_chronology_text_blind_v2_en_headline_ab_v1_latest.json"
SIDEcar = ROOT / "docs/final/artifacts/fixtures/logos_chronology_historical_era_gold_en_headlines_v1.json"


def test_en_headline_sidecar_covers_gold_events() -> None:
    gold = json.loads(
        (ROOT / "docs/final/artifacts/fixtures/logos_chronology_historical_era_gold_v1.json").read_text(
            encoding="utf-8"
        )
    )
    side = json.loads(SIDEcar.read_text(encoding="utf-8"))
    gold_ids = {e["event_id"] for e in gold["events"]}
    en_ids = {h["event_id"] for h in side["headlines"]}
    assert gold_ids == en_ids


def test_en_headline_ab_runs() -> None:
    rc = subprocess.call([sys.executable, str(AB), "--skip-ko-rerun"], cwd=str(ROOT))
    assert rc == 0
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    cmp_ = doc["compare"]
    assert cmp_["train_holdout_hit_at_1_ko"] is not None
    assert cmp_["train_holdout_hit_at_1_en"] is not None
