#!/usr/bin/env python3
"""[HYPO] Lens decomposition for wrong-direction BTC days (from miss report + per-date rows)."""
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

DEFAULT_MISS = ROOT / "reports/btrack_headline_miss_report_v1_latest.json"
DEFAULT_PER_DATE = ROOT / "reports/btrack_ensemble_per_date_directions_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/btrack_wrong_direction_lens_report_v1_latest.json"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _lens_sign(score: Any) -> str:
    try:
        v = float(score)
    except (TypeError, ValueError):
        return "?"
    if v > 0.03:
        return "bull"
    if v < -0.03:
        return "bear"
    return "flat"


def build_report(miss_doc: dict[str, Any], per_date_doc: dict[str, Any]) -> dict[str, Any]:
    by_date = {
        str(r.get("eval_date"))[:10]: r
        for r in (per_date_doc.get("rows") or [])
        if isinstance(r, dict) and str(r.get("instrument") or "").lower() == "btc"
    }
    wrong_rows: list[dict[str, Any]] = []
    for m in miss_doc.get("misses") or []:
        if not isinstance(m, dict) or m.get("miss_kind") != "wrong_direction":
            continue
        ed = str(m.get("eval_date") or "")[:10]
        row = by_date.get(ed) or {}
        lv = row.get("lens_values") if isinstance(row.get("lens_values"), dict) else {}
        weights = row.get("weights") if isinstance(row.get("weights"), dict) else {}
        lens_detail = {}
        for name, blob in lv.items():
            if not isinstance(blob, dict):
                continue
            sc = blob.get("score")
            w = weights.get(name)
            lens_detail[name] = {
                "score": sc,
                "confidence": blob.get("confidence"),
                "weight": w,
                "implied_sign": _lens_sign(sc),
            }
        price = lens_detail.get("price") or {}
        macro = lens_detail.get("macro") or {}
        wrong_rows.append(
            {
                "eval_date": ed,
                "predicted_direction": m.get("predicted_direction"),
                "actual_direction": m.get("actual_direction"),
                "preliminary_direction": row.get("preliminary_direction"),
                "weighted_score": row.get("weighted_score"),
                "confidence": row.get("confidence"),
                "lens_values": lens_detail,
                "diagnosis": _diagnose(price, macro, str(m.get("predicted_direction"))),
            }
        )
    price_bull_wrong = sum(
        1
        for r in wrong_rows
        if (r.get("lens_values") or {}).get("price", {}).get("implied_sign") == "bull"
    )
    return {
        "schema": "btrack_wrong_direction_lens_report_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "n_wrong_direction_days": len(wrong_rows),
        "summary": {
            "price_lens_bull_on_wrong_days": price_bull_wrong,
            "note": (
                "Wrong-direction days often coincide with price lens bull bias while actual was bear; "
                "macro/news/myeongni adjustments did not flip ensemble sign."
            ),
        },
        "wrong_direction_days": wrong_rows,
        "operator_line": (
            f"- [MKM-WRONG-DIR-LENS] {len(wrong_rows)} wrong_dir days; "
            f"price_lens_bull={price_bull_wrong}/{len(wrong_rows)} on those dates"
        ),
    }


def _diagnose(price: dict[str, Any], macro: dict[str, Any], pred: str) -> str:
    ps = price.get("implied_sign")
    if pred == "bull" and ps == "bull":
        return "price_lens_aligned_wrong_with_actual_bear"
    if pred == "bull" and ps != "bull":
        return "ensemble_bull_despite_non_bull_price_lens"
    return "mixed_lens_ensemble_sign"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--miss-report", type=Path, default=DEFAULT_MISS)
    ap.add_argument("--per-date-json", type=Path, default=DEFAULT_PER_DATE)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    if not args.miss_report.is_file() or not args.per_date_json.is_file():
        print("Missing miss or per-date JSON.", file=sys.stderr)
        return 2
    report = build_report(_load(args.miss_report), _load(args.per_date_json))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    print(report["operator_line"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
