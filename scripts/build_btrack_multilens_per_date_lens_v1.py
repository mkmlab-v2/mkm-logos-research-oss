#!/usr/bin/env python3
"""Build causal per-date multilens panel (myeongni/sasang/logos) — no paid API."""
from __future__ import annotations

import argparse
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCORE = ROOT / "docs/final/artifacts/btrack_prophecy_score_latest.json"
DEFAULT_OUT_JSON = ROOT / "reports/btrack_multilens_per_date_lens_v1_latest.json"
DEFAULT_OUT_JSONL = ROOT / "reports/btrack_phase3_per_date_lens_panel_v1_latest.jsonl"
DEFAULT_OUT_META = ROOT / "reports/btrack_phase3_per_date_lens_panel_v1_latest.meta.json"


def _load_core():
    spec = importlib.util.spec_from_file_location(
        "btrack_multilens_per_date_core_v1",
        ROOT / "scripts" / "btrack_multilens_per_date_core_v1.py",
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(p).replace("\\", "/")


def _panel_compat_row(row: dict[str, Any]) -> dict[str, Any]:
    """Shrink for phase3 multilens aux eval (backward compatible keys)."""
    lenses = row.get("lenses") if isinstance(row.get("lenses"), dict) else {}
    my = lenses.get("myeongni") if isinstance(lenses.get("myeongni"), dict) else {}
    sa = lenses.get("sasang") if isinstance(lenses.get("sasang"), dict) else {}
    lo = lenses.get("logos") if isinstance(lenses.get("logos"), dict) else {}
    return {
        "eval_date": row.get("eval_date"),
        "instrument": row.get("instrument"),
        "predicted_direction": row.get("predicted_direction"),
        "actual_direction": row.get("actual_direction"),
        "daily_return": row.get("daily_return"),
        "price_predicted_sign": row.get("price_predicted_sign"),
        "lens": {
            "logos_sign": lo.get("sign"),
            "logos_data_quality": lo.get("data_quality"),
            "logos_non_gating": lo.get("non_gating"),
            "myeongni_sign": 1
            if (my.get("direction_score") or 0) > 0
            else (-1 if (my.get("direction_score") or 0) < 0 else 0),
            "myeongni_matched_calendar_day": my.get("matched_calendar_day"),
            "myeongni_data_quality": my.get("data_quality"),
            "sasang_sign": 1
            if (sa.get("direction_score") or 0) > 0
            else (-1 if (sa.get("direction_score") or 0) < 0 else 0),
            "sasang_matched_calendar_day": sa.get("matched_calendar_day"),
            "sasang_data_quality": sa.get("data_quality"),
            "non_neutral_lens_count": sum(
                1
                for s in (
                    lo.get("sign"),
                    1 if (my.get("direction_score") or 0) > 0 else (-1 if (my.get("direction_score") or 0) < 0 else 0),
                    1 if (sa.get("direction_score") or 0) > 0 else (-1 if (sa.get("direction_score") or 0) < 0 else 0),
                )
                if s not in (None, 0)
            ),
            "lens_majority_sign": row.get("lens_majority_sign"),
        },
        "lens_disagrees_with_price_pred": row.get("lens_disagrees_with_price_pred"),
        "loop_mode": row.get("loop_mode"),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--instrument", default="btc", choices=("btc", "kospi", "all"))
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT_JSON)
    ap.add_argument("--output-jsonl", type=Path, default=DEFAULT_OUT_JSONL)
    ap.add_argument("--output-meta", type=Path, default=DEFAULT_OUT_META)
    ap.add_argument("--momentum-window", type=int, default=5)
    ap.add_argument("--skip-jsonl-compat", action="store_true")
    args = ap.parse_args(argv)

    if not args.score_json.is_file():
        print(f"MISSING score: {args.score_json}", file=__import__("sys").stderr)
        return 2

    core = _load_core()
    score = json.loads(args.score_json.read_text(encoding="utf-8-sig"))
    rows = [x for x in (score.get("rows") or []) if isinstance(x, dict)]
    doc = core.build_document(
        rows,
        instrument=args.instrument,
        momentum_window=max(1, int(args.momentum_window)),
    )
    doc["generated_at_utc"] = _utc_now()

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output_json.resolve()} ({doc['n_rows']} rows)")

    if not args.skip_jsonl_compat:
        compat = [_panel_compat_row(r) for r in doc.get("rows") or []]
        with args.output_jsonl.open("w", encoding="utf-8") as f:
            for row in compat:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        meta = {
            "schema": "btrack_phase3_per_date_lens_panel_v1",
            "generated_at_utc": _utc_now(),
            "research_only": True,
            "source": "build_btrack_multilens_per_date_lens_v1",
            "full_document": _rel(args.output_json),
            "n_rows": len(compat),
            "loop_mode": "causal_calendar_jsonl_per_date_v1",
            "paid_api": False,
            "direction_promotion_allowed": False,
        }
        args.output_meta.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"WROTE: {args.output_jsonl.resolve()} ({len(compat)} rows)")
        print(f"WROTE: {args.output_meta.resolve()}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
