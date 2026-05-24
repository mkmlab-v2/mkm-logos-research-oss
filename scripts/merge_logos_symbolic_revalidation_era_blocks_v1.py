#!/usr/bin/env python3
"""Merge era blind eval + AB summaries into logos_symbolic_revalidation_report_latest.json."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REVAL = ROOT / "docs/final/artifacts/logos_symbolic_revalidation_report_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _slim(path: Path) -> dict[str, Any]:
    d = json.loads(path.read_text(encoding="utf-8"))
    return {k: d[k] for k in ("schema", "generated_at_utc", "status", "summary", "known_limitations") if k in d}


def main() -> int:
    if not REVAL.is_file():
        print(f"MISSING: {REVAL}")
        return 2
    doc = json.loads(REVAL.read_text(encoding="utf-8"))
    pairs = [
        ("non_synthetic_era_blind_eval_historical_gold_tags_v1", "logos_chronology_era_blind_eval_v1_latest.json"),
        ("non_synthetic_era_blind_eval_historical_text_blind_v1", "logos_chronology_era_blind_eval_text_blind_v1_latest.json"),
        ("non_synthetic_era_blind_eval_hardset_v1", "logos_chronology_hardset_text_blind_eval_v1_latest.json"),
    ]
    for key, rel in pairs:
        p = ROOT / "docs/final/artifacts" / rel
        if p.is_file():
            doc[key] = _slim(p)
    ab = ROOT / "docs/final/artifacts/logos_chronology_era_modern_boost_ab_v1_latest.json"
    if ab.is_file():
        doc["non_synthetic_era_modern_boost_ab_v1"] = json.loads(ab.read_text(encoding="utf-8"))
    tab = ROOT / "docs/final/artifacts/logos_chronology_era_tier_boost_ab_v1_latest.json"
    if tab.is_file():
        doc["non_synthetic_era_tier_boost_ab_v1"] = json.loads(tab.read_text(encoding="utf-8"))
    tier_eval = ROOT / "docs/final/artifacts/logos_chronology_era_blind_eval_tier_v1_latest.json"
    if tier_eval.is_file():
        doc["non_synthetic_era_blind_eval_tier_v1_gold_tags"] = _slim(tier_eval)
    h2 = ROOT / "docs/final/artifacts/logos_chronology_hardset_text_blind_v2_eval_v1_latest.json"
    if h2.is_file():
        doc["non_synthetic_era_blind_eval_hardset_v2"] = _slim(h2)
    cmp_h = ROOT / "docs/final/artifacts/logos_chronology_hardset_gold_mode_compare_v1_latest.json"
    if cmp_h.is_file():
        doc["non_synthetic_hardset_gold_mode_compare_v1"] = json.loads(cmp_h.read_text(encoding="utf-8"))
    doc["non_synthetic_era_blind_appended_at_utc"] = _now()
    doc["era_eval_policy_note"] = (
        "modern_boost default 0.0 (AB v1: narrative tier +0.10 hit@1 with boost off). "
        "[HYPO]/NON_GATING; not price prophecy."
    )
    REVAL.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"MERGED: {REVAL}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
