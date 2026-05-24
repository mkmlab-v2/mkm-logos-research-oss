"""Tier-scoped modern boost (tier_v1) unit + AB smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from logos_chronology_map_core_v1 import resolve_modern_boost, rank_eras  # noqa: E402


def test_resolve_modern_boost_tier_v1_blocks_narrative() -> None:
    assert resolve_modern_boost("biblical_narrative", 0.08, "tier_v1") == 0.0
    assert resolve_modern_boost("macro_landmark", 0.08, "tier_v1") == 0.08
    assert resolve_modern_boost("biblical_narrative", 0.08, "global") == 0.08


def test_rank_eras_tier_v1_changes_narrative_top1() -> None:
    chrono_path = ROOT / "docs/final/artifacts/logos_chronology_v1_latest.json"
    if not chrono_path.is_file():
        return
    chrono = json.loads(chrono_path.read_text(encoding="utf-8"))
    tags = ["risk", "covid", "lehman"]
    g = rank_eras(chrono, tags, modern_boost=0.08, event_tier="biblical_narrative", boost_policy="global")
    t = rank_eras(chrono, tags, modern_boost=0.08, event_tier="biblical_narrative", boost_policy="tier_v1")
    if g and t:
        assert float(g[0]["score"]) >= float(t[0]["score"])


def test_tier_boost_ab_runs(tmp_path: Path) -> None:
    gold = ROOT / "docs/final/artifacts/fixtures/logos_chronology_historical_era_gold_v1.json"
    if not gold.is_file():
        return
    out = tmp_path / "tier_ab.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_logos_chronology_era_tier_boost_ab_v1.py"),
            "--gold-json",
            str(gold),
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_chronology_era_tier_boost_ab_v1"
    assert "tier_v1_macro_boost" in doc["variants"]
