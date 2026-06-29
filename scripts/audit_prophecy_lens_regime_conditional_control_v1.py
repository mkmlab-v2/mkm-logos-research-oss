#!/usr/bin/env python3
"""[HYPO] Regime-conditional always_bull control counterfactual audit (prod gt unchanged)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WF = ROOT / "reports/prophecy_per_date_combo_walkforward_recommended_chain_v1_latest.json"
DEFAULT_SCORE = ROOT / "reports/btrack_prophecy_score_recommended_eval_chain_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/prophecy_lens_regime_conditional_control_audit_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        o = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return o if isinstance(o, dict) else {}


def _rel(p: Path) -> str:
    try:
        return str(p.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p)


def _kospi_rows_by_date(score_doc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for r in score_doc.get("rows") or []:
        if not isinstance(r, dict):
            continue
        if str(r.get("instrument") or "").lower() != "kospi":
            continue
        d = str(r.get("eval_date") or "")[:10]
        if d:
            out[d] = r
    return out


def _bull_fraction(rows: list[dict[str, Any]]) -> float | None:
    if not rows:
        return None
    bull = sum(1 for r in rows if str(r.get("actual_direction") or "").strip().lower() == "bull")
    return round(bull / len(rows), 6)


def _lookback_bull(train_dates: list[str], by_date: dict[str, dict[str, Any]], n: int) -> float | None:
    uniq = sorted({str(d)[:10] for d in train_dates if d})
    if not uniq:
        return None
    tail = uniq[-n:] if len(uniq) >= n else uniq
    rows = [by_date[d] for d in tail if d in by_date]
    return _bull_fraction(rows)


def _gt_pass(test_acc: float, control: float | None) -> bool | None:
    if control is None:
        return None
    return test_acc > control


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--walkforward-json", type=Path, default=DEFAULT_WF)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    wf = _load(args.walkforward_json)
    score = _load(args.score_json)
    if not wf or not score:
        print("Missing walkforward or score JSON", file=__import__("sys").stderr)
        return 2

    by_date = _kospi_rows_by_date(score)
    fold_rows: list[dict[str, Any]] = []

    for fold in wf.get("folds") or []:
        if not isinstance(fold, dict):
            continue
        fi = int(fold.get("fold_index", -1))
        train_dates = [str(d)[:10] for d in (fold.get("train_dates") or [])]
        test_dates = [str(d)[:10] for d in (fold.get("test_dates") or [])]
        train_rows = [by_date[d] for d in train_dates if d in by_date]
        test_rows = [by_date[d] for d in test_dates if d in by_date]
        test = fold.get("test") if isinstance(fold.get("test"), dict) else {}
        test_acc = float(test.get("accuracy") or 0.0)
        prod_control = float(test.get("always_bull_control") or _bull_fraction(test_rows) or 0.0)
        train_bull = float(fold.get("train_bull_fraction") or _bull_fraction(train_rows) or 0.0)
        test_bull = _bull_fraction(test_rows) or prod_control
        lb20 = _lookback_bull(train_dates, by_date, 20)
        lb40 = _lookback_bull(train_dates, by_date, 40)

        controls: dict[str, float | None] = {
            "prod_always_bull_test": prod_control,
            "train_bull_fraction": round(train_bull, 6),
            "test_bull_fraction": round(float(test_bull), 6),
            "train_lookback_20_bull": lb20,
            "train_lookback_40_bull": lb40,
            "regime_heavy_bull_train_control": (
                round(train_bull, 6) if train_bull >= 0.60 else round(float(test_bull), 6)
            ),
            "regime_bear_train_stricter_control": (
                round(float(test_bull) + 0.02, 6) if train_bull < 0.55 else round(float(test_bull), 6)
            ),
            "max_train_or_test_bull": round(max(train_bull, float(test_bull)), 6),
        }
        gt_map = {k: _gt_pass(test_acc, v) for k, v in controls.items()}

        fold_rows.append(
            {
                "fold_index": fi,
                "test_accuracy": round(test_acc, 6),
                "margin_vs_prod_control": round(test_acc - prod_control, 6),
                "controls": controls,
                "gt_pass_by_control": gt_map,
                "prod_gt_pass": gt_map.get("prod_always_bull_test"),
                "counterfactual_gt_pass_ids": [k for k, v in gt_map.items() if k != "prod_always_bull_test" and v is True],
            }
        )

    n_folds = len(fold_rows)
    prod_gt = sum(1 for f in fold_rows if f.get("prod_gt_pass"))
    counterfactual_ids: dict[str, int] = {}
    for f in fold_rows:
        for cid in f.get("counterfactual_gt_pass_ids") or []:
            counterfactual_ids[cid] = counterfactual_ids.get(cid, 0) + 1

    best_counterfactual = max(counterfactual_ids.items(), key=lambda kv: kv[1], default=(None, 0))
    verdict_ko = (
        f"prod gt {prod_gt}/{n_folds}; regime-conditional comparator swap은 research counterfactual only — "
        "prod gate 정의 변경 없이 승격 근거 아님."
    )
    if best_counterfactual[0] and best_counterfactual[1] > prod_gt:
        verdict_ko += (
            f" 일부 대체 control({best_counterfactual[0]})은 {best_counterfactual[1]}/{n_folds} fold gt 통과 counterfactual."
        )
    else:
        verdict_ko += " 대체 regime-conditional control으로도 prod test_accuracy 대비 gt 우위 fold 증가 없음."

    report: dict[str, Any] = {
        "schema": "prophecy_lens_regime_conditional_control_audit_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "track_a_auto_promote": False,
        "send_gate": "HOLD",
        "prod_comparator_unchanged": "gt vs test-fold always_bull_control",
        "inputs": {
            "walkforward_json": _rel(args.walkforward_json),
            "score_json": _rel(args.score_json),
        },
        "folds": fold_rows,
        "summary": {
            "n_folds": n_folds,
            "prod_gt_pass_folds": prod_gt,
            "counterfactual_gt_pass_counts": counterfactual_ids,
            "best_counterfactual_control": best_counterfactual[0],
            "best_counterfactual_gt_pass_folds": best_counterfactual[1],
        },
        "verdict_ko": verdict_ko,
        "ledger_line": (
            f"Lens regime-conditional control audit: prod gt {prod_gt}/{n_folds}; "
            f"best counterfactual={(best_counterfactual[0] or 'none')} {best_counterfactual[1]}/{n_folds}; "
            "prod comparator unchanged; no oper promotion."
        ),
        "operator_lines": [
            "- [LENS-P3-AUDIT] research_only; prod comparator=gt unchanged.",
            f"- [LENS-P3-AUDIT] prod_gt={prod_gt}/{n_folds} best_counterfactual={best_counterfactual[0]} "
            f"folds={best_counterfactual[1]}.",
        ],
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    for line in report["operator_lines"]:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
