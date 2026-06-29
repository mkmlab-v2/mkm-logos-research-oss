#!/usr/bin/env python3
"""Commercial-depth closure gate for Logos Track B (research_only, non_gating)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PRESETS = ROOT / "docs/final/artifacts/LOGOS_TRACK_B_THEME_PRESETS_V1.json"
ART = ROOT / "docs/final/artifacts"
OUT_DEFAULT = ROOT / "docs/final/artifacts/logos_commercial_depth_closure_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return {}


def _theme_ids() -> list[str]:
    presets = _load(PRESETS)
    return list((presets.get("themes") or {}).keys())


def build() -> dict[str, Any]:
    theme_ids = _theme_ids()
    deep_doc = _load(ROOT / "reports/logos_track_b_themed_deep_push_v1_latest.json")
    heatmap = _load(ROOT / "reports/logos_canon_book_coverage_heatmap_v1_latest.json")
    key_v2 = _load(ROOT / "reports/verse_metadata_shadow_v2_latest.json")
    dual_ab = _load(ROOT / "reports/logos_lexicon_4d_dual_ab_report_v1_latest.json")
    closure_100 = _load(ROOT / "docs/final/artifacts/logos_100pct_closure_v1_latest.json")

    deep_themes = {r.get("theme_id"): r for r in (deep_doc.get("themes") or [])}
    citation_valid = 0
    citation_locked = 0
    for tid in theme_ids:
        locked = _load(ART / f"logos_deep_research_distill_{tid}_citation_lock_latest.json")
        lock = locked.get("citation_lock") or {}
        evidence = locked.get("evidence_refs") or []
        locked_count = int(lock.get("locked_count") or 0)
        if locked_count > 0:
            citation_locked += 1
        # Stub citation-lock mode: hash-locked refs >= 3 and covers evidence set
        if locked_count >= 3 and locked_count >= max(1, len(evidence)):
            citation_valid += 1

    min_themes = max(10, len(theme_ids) - 2)
    key_rows = int((key_v2.get("summary") or {}).get("rows") or 0)
    hm = heatmap.get("summary") or {}

    checks = {
        "theme_preset_count": {
            "passed": len(theme_ids) >= 12,
            "value": len(theme_ids),
            "target": 12,
        },
        "deep_push_all_ok": {
            "passed": deep_doc.get("all_ok") is True,
            "value": deep_doc.get("all_ok"),
        },
        "citation_valid_themes": {
            "passed": citation_valid >= min_themes,
            "value": citation_valid,
            "target": min_themes,
        },
        "citation_locked_themes": {
            "passed": citation_locked >= min_themes,
            "value": citation_locked,
            "target": min_themes,
        },
        "key_verse_v2_density": {
            "passed": key_rows >= 80,
            "value": key_rows,
            "target": 80,
        },
        "book_heatmap_present": {
            "passed": int(hm.get("book_count") or 0) >= 40,
            "value": hm.get("book_count"),
            "target": 40,
        },
        "lexicon_dual_ab": {
            "passed": dual_ab.get("shadow_recommendation") in (
                "min1_shadow_candidate",
                "min1_ab_watch",
                "hold_baseline",
            ),
            "value": dual_ab.get("shadow_recommendation"),
        },
        "base_closure_100pct": {
            "passed": closure_100.get("closure_ok") is True,
            "value": closure_100.get("closure_ok"),
        },
    }
    closure_ok = all(c.get("passed") for c in checks.values())

    return {
        "schema": "logos_commercial_depth_closure_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "closure_ok": closure_ok,
        "commercial_depth_tier": "research_product_ready" if closure_ok else "depth_expansion_in_progress",
        "checks": checks,
        "theme_ids": theme_ids,
        "track_wall": {
            "track_a_auto_promotion": False,
            "live_trading_trigger": False,
            "ms_headline_merge_forbidden": True,
        },
        "reproduce": "py scripts/build_logos_commercial_depth_closure_gate_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "closure_ok": doc["closure_ok"], "tier": doc["commercial_depth_tier"]}, ensure_ascii=False))
    return 0 if doc["closure_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
