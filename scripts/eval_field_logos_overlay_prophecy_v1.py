#!/usr/bin/env python3
"""Evaluate Field×Logos overlay predictions against holdout gold (B-track)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from field_logos_overlay_prophecy_common_v1 import (  # noqa: E402
    DEFAULT_HOLDOUT,
    DEFAULT_OVERLAY_OUT,
    load_holdout_items,
    read_json,
    rel_path,
)

DEFAULT_EVAL_OUT = ROOT / "reports/field_logos_overlay_prophecy_eval_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _score_prediction(pred: dict[str, Any], gold: dict[str, Any]) -> dict[str, Any]:
    logos = pred.get("logos_axis") if isinstance(pred.get("logos_axis"), dict) else {}
    bridges = [str(b) for b in (logos.get("bridge_artifacts") or [])]
    verses = [str(v) for v in (logos.get("verse_ids") or [])]
    lanes = [str(x) for x in (logos.get("theme_lanes_active") or [])]

    expected_bridge = str(gold.get("expected_bridge_substring") or "")
    bridge_hits = [b for b in bridges if expected_bridge and expected_bridge in b]
    bridge_ok = len(bridge_hits) >= int(gold.get("min_paths_from_expected_bridge") or 1)

    expected_verses = [str(v) for v in (gold.get("expected_verse_ids") or [])]
    verse_ok = True
    missing_verses: list[str] = []
    if expected_verses:
        verse_ok = all(any(ev in v for v in verses) for ev in expected_verses)
        missing_verses = [ev for ev in expected_verses if not any(ev in v for v in verses)]

    theme_lane = str(gold.get("theme_lane") or "")
    lane_ok = (not theme_lane) or (theme_lane in lanes)

    field_axis = pred.get("field_axis") if isinstance(pred.get("field_axis"), dict) else {}
    field_ok = bool(field_axis.get("field_alignment_ok", True))

    passed = bridge_ok and verse_ok and lane_ok and field_ok
    return {
        "prediction_id": pred.get("prediction_id"),
        "holdout_id": gold.get("id"),
        "query_ko": pred.get("query_ko"),
        "passed": passed,
        "checks": {
            "bridge_ok": bridge_ok,
            "verse_ok": verse_ok,
            "lane_ok": lane_ok,
            "field_ok": field_ok,
        },
        "bridge_hits": bridge_hits,
        "missing_verses": missing_verses,
        "top_match_score": logos.get("top_match_score"),
        "confidence_0_1": (pred.get("fused_hypothesis") or {}).get("confidence_0_1"),
    }


def eval_overlay(overlay: dict[str, Any], holdout_path: Path) -> dict[str, Any]:
    gold_by_query = {str(it["query_ko"]): it for it in load_holdout_items(holdout_path)}
    rows: list[dict[str, Any]] = []
    for pred in overlay.get("predictions") or []:
        if not isinstance(pred, dict):
            continue
        gold = gold_by_query.get(str(pred.get("query_ko") or ""))
        if not gold:
            rows.append({"prediction_id": pred.get("prediction_id"), "passed": False, "reason": "no_gold"})
            continue
        rows.append(_score_prediction(pred, gold))

    n = len(rows)
    passed_n = sum(1 for r in rows if r.get("passed"))
    pass_rate = (passed_n / n) if n else 0.0
    return {
        "schema": "field_logos_overlay_prophecy_eval_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tier": "[HYPO]",
        "non_gating": True,
        "overlay_path": None,
        "parameters": overlay.get("parameters"),
        "summary": {
            "total": n,
            "passed": passed_n,
            "pass_rate": round(pass_rate, 4),
            "eval_ok": pass_rate >= 0.5,
        },
        "rows": rows,
        "track_wall": {
            "a_track_auto_promotion": False,
            "live_trading_trigger": False,
            "evolution_parameter_only": True,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--overlay-json", type=Path, default=DEFAULT_OVERLAY_OUT)
    ap.add_argument("--holdout-json", type=Path, default=DEFAULT_HOLDOUT)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_EVAL_OUT)
    ap.add_argument("--strict", action="store_true", help="Exit 1 when pass_rate < 0.5")
    args = ap.parse_args()

    overlay_path = args.overlay_json if args.overlay_json.is_absolute() else ROOT / args.overlay_json
    holdout_path = args.holdout_json if args.holdout_json.is_absolute() else ROOT / args.holdout_json
    overlay = read_json(overlay_path)
    if not overlay:
        raise SystemExit(f"missing overlay: {overlay_path}")

    doc = eval_overlay(overlay, holdout_path)
    doc["overlay_path"] = rel_path(overlay_path)
    out = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ok = bool(doc.get("summary", {}).get("eval_ok"))
    print(json.dumps({"ok": ok, "pass_rate": doc["summary"]["pass_rate"], "out": str(out)}, ensure_ascii=False))
    if args.strict and not ok:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
