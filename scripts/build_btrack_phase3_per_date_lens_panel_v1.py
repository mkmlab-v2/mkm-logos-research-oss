#!/usr/bin/env python3
"""Build per-eval_date lens panel for Phase 3 join / multilens aux eval (research_only).

Uses calendar JSONL as-of semantics + global Logos independent lens snapshot.
Does not run live lens engines unless operator passes --run-lens-engines (future hook).
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCORE = ROOT / "docs/final/artifacts/btrack_prophecy_score_latest.json"
DEFAULT_OUT_JSONL = ROOT / "reports/btrack_phase3_per_date_lens_panel_v1_latest.jsonl"
DEFAULT_OUT_META = ROOT / "reports/btrack_phase3_per_date_lens_panel_v1_latest.meta.json"
SCHEMA = "btrack_phase3_per_date_lens_panel_v1"


def _load_lens_asof():
    spec = importlib.util.spec_from_file_location(
        "btrack_phase3_lens_asof_v1",
        ROOT / "scripts" / "btrack_phase3_lens_asof_v1.py",
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


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build_panel_rows(
    score_rows: list[dict[str, Any]],
    *,
    lens_mod: Any,
    instrument: str,
    sasang_jsonl: Path,
    myeongni_jsonl: Path,
    logos_lens: Path,
) -> list[dict[str, Any]]:
    logos_sign, logos_q = lens_mod.logos_sign_from_independent_lens(logos_lens)
    sasang_by_day = lens_mod.jsonl_last_row_by_calendar_day(sasang_jsonl)
    myeongni_by_day = lens_mod.jsonl_last_row_by_calendar_day(myeongni_jsonl)
    out: list[dict[str, Any]] = []
    for r in score_rows:
        if not isinstance(r, dict):
            continue
        inst = str(r.get("instrument") or "").strip().lower()
        if instrument != "all" and inst != instrument:
            continue
        ed = str(r.get("eval_date") or "")[:10]
        if len(ed) != 10:
            continue
        lens = lens_mod.lens_row_for_eval_date(
            ed,
            logos_sign=logos_sign,
            logos_quality=logos_q,
            sasang_by_day=sasang_by_day,
            myeongni_by_day=myeongni_by_day,
        )
        price_sign = lens_mod.dir_to_sign(str(r.get("predicted_direction") or "neutral"))
        majority = int(lens.get("lens_majority_sign") or 0)
        out.append(
            {
                "eval_date": ed,
                "instrument": inst,
                "predicted_direction": r.get("predicted_direction"),
                "actual_direction": r.get("actual_direction"),
                "daily_return": r.get("daily_return"),
                "price_predicted_sign": price_sign,
                "lens": lens,
                "lens_disagrees_with_price_pred": (
                    price_sign != 0 and majority != 0 and price_sign != majority
                ),
                "research_only": True,
                "hypothesis_tag": "[HYPO]",
                "role_ko": "size/confidence 보조·관측만; 방향 승격·Track A 합선 금지.",
            }
        )
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--instrument", default="btc", choices=("btc", "kospi", "all"))
    ap.add_argument("--sasang-jsonl", type=Path, default=None)
    ap.add_argument("--myeongni-jsonl", type=Path, default=None)
    ap.add_argument("--logos-lens-json", type=Path, default=None)
    ap.add_argument("--out-jsonl", type=Path, default=DEFAULT_OUT_JSONL)
    ap.add_argument("--out-meta", type=Path, default=DEFAULT_OUT_META)
    args = ap.parse_args(argv)

    lens_mod = _load_lens_asof()
    sasang = args.sasang_jsonl or lens_mod.DEFAULT_SASANG_JSONL
    myeongni = args.myeongni_jsonl or lens_mod.DEFAULT_MYEONGNI_JSONL
    logos = args.logos_lens_json or lens_mod.DEFAULT_LOGOS_LENS

    if not args.score_json.is_file():
        print(f"MISSING score: {args.score_json}", file=__import__("sys").stderr)
        return 2

    score = _load_json(args.score_json)
    rows = [x for x in (score.get("rows") or []) if isinstance(x, dict)]
    panel = build_panel_rows(
        rows,
        lens_mod=lens_mod,
        instrument=args.instrument,
        sasang_jsonl=sasang,
        myeongni_jsonl=myeongni,
        logos_lens=logos,
    )

    args.out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.out_jsonl.open("w", encoding="utf-8") as f:
        for row in panel:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    n_disagree = sum(1 for r in panel if r.get("lens_disagrees_with_price_pred"))
    meta = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "inputs": {
            "score_json": _rel(args.score_json),
            "sasang_jsonl": _rel(sasang),
            "myeongni_jsonl": _rel(myeongni),
            "logos_lens_json": _rel(logos),
        },
        "instrument_filter": args.instrument,
        "n_rows": len(panel),
        "n_lens_disagrees_with_price_pred": n_disagree,
        "direction_promotion_allowed": False,
        "note_ko": "캘린더 stub as-of + Logos 글로벌; 실측 엔진 per-date는 별도 run_lens_* 체인.",
    }
    args.out_meta.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_jsonl.resolve()} ({len(panel)} rows)")
    print(f"WROTE: {args.out_meta.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
