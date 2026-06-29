#!/usr/bin/env python3
"""[HYPO] Decompose BTC lens WF folds by test-window bull/bear regime using score rows."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WF = ROOT / "reports/prophecy_per_date_combo_walkforward_recommended_chain_v1_latest.json"
DEFAULT_SCORE = ROOT / "reports/btrack_prophecy_score_recommended_eval_chain_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/btc_lens_wf_fold_regime_decomposition_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _btc_by_date(score: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for r in score.get("rows") or []:
        if not isinstance(r, dict):
            continue
        if str(r.get("instrument") or "").lower() != "btc":
            continue
        ed = str(r.get("eval_date") or "")[:10]
        if len(ed) == 10:
            out[ed] = r
    return out


def _subset_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"n": 0, "accuracy": None, "bull_actual_n": 0, "bear_actual_n": 0}
    hits = sum(1 for r in rows if r.get("predicted_direction") == r.get("actual_direction"))
    bull = sum(1 for r in rows if str(r.get("actual_direction")) == "bull")
    bear = sum(1 for r in rows if str(r.get("actual_direction")) == "bear")
    return {
        "n": len(rows),
        "accuracy": round(hits / len(rows), 6),
        "bull_actual_n": bull,
        "bear_actual_n": bear,
        "bull_actual_frac": round(bull / len(rows), 6),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--wf-json", type=Path, default=DEFAULT_WF)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    wf_path = args.wf_json if args.wf_json.is_absolute() else ROOT / args.wf_json
    score_path = args.score_json if args.score_json.is_absolute() else ROOT / args.score_json
    wf = _load(wf_path)
    score = _load(score_path)
    by_date = _btc_by_date(score)

    fold_rows: list[dict[str, Any]] = []
    for fold in wf.get("folds") or []:
        if not isinstance(fold, dict):
            continue
        fi = fold.get("fold_index")
        test_dates = [str(d)[:10] for d in (fold.get("test_dates") or [])]
        test_rows = [by_date[d] for d in test_dates if d in by_date]
        bull_rows = [r for r in test_rows if str(r.get("actual_direction")) == "bull"]
        bear_rows = [r for r in test_rows if str(r.get("actual_direction")) == "bear"]
        wrong = [
            {
                "eval_date": str(r.get("eval_date"))[:10],
                "pred": r.get("predicted_direction"),
                "actual": r.get("actual_direction"),
                "daily_return": r.get("daily_return"),
            }
            for r in test_rows
            if r.get("predicted_direction") != r.get("actual_direction")
        ]
        fold_rows.append(
            {
                "fold_index": fi,
                "wf_test_accuracy": (fold.get("test") or {}).get("accuracy"),
                "wf_always_bull_control": (fold.get("test") or {}).get("always_bull_control"),
                "wf_test_beats_always_bull": fold.get("test_beats_always_bull"),
                "best_params_from_train": fold.get("best_params_from_train"),
                "score_panel_all": _subset_metrics(test_rows),
                "score_panel_bull_actual": _subset_metrics(bull_rows),
                "score_panel_bear_actual": _subset_metrics(bear_rows),
                "miss_dates_top": wrong[:10],
                "miss_n": len(wrong),
            }
        )

    worst = min(
        (f for f in fold_rows if isinstance(f.get("wf_test_accuracy"), (int, float))),
        key=lambda x: float(x["wf_test_accuracy"]),
        default=None,
    )
    doc = {
        "schema": "btc_lens_wf_fold_regime_decomposition_v1",
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "generated_at_utc": _utc_now(),
        "wf_json": str(wf_path.relative_to(ROOT.resolve())).replace("\\", "/"),
        "score_json": str(score_path.relative_to(ROOT.resolve())).replace("\\", "/"),
        "note": "score_panel uses post-processed btrack_prophecy_score rows (ensemble+rules), not raw lens combo replay.",
        "folds": fold_rows,
        "worst_fold_by_wf_test_accuracy": worst,
    }
    out = args.output if args.output.is_absolute() else ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out} folds={len(fold_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
