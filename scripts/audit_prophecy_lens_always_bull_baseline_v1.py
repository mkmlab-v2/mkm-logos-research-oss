#!/usr/bin/env python3
"""[HYPO] Audit always_bull control vs alternative baselines on prod lens WF folds."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WF = ROOT / "reports/prophecy_per_date_combo_walkforward_recommended_chain_v1_latest.json"
DEFAULT_SCORE = ROOT / "reports/btrack_prophecy_score_recommended_eval_chain_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/prophecy_lens_always_bull_baseline_audit_v1_latest.json"


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


def _actual_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    c = {"bull": 0, "bear": 0, "neutral": 0, "other": 0}
    for r in rows:
        ad = str(r.get("actual_direction") or "").strip().lower()
        if ad in c:
            c[ad] += 1
        else:
            c["other"] += 1
    return c


def _baseline_rates(counts: dict[str, int], n: int) -> dict[str, float | None]:
    if n <= 0:
        return {
            "always_bull_test": None,
            "always_bear_test": None,
            "always_neutral_test": None,
            "majority_class_test": None,
        }
    bull = counts["bull"] / n
    bear = counts["bear"] / n
    neu = counts["neutral"] / n
    return {
        "always_bull_test": round(bull, 6),
        "always_bear_test": round(bear, 6),
        "always_neutral_test": round(neu, 6),
        "majority_class_test": round(max(bull, bear, neu), 6),
    }


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
        test_dates = [str(d)[:10] for d in (fold.get("test_dates") or [])]
        test_rows = [by_date[d] for d in test_dates if d in by_date]
        n = len(test_rows)
        counts = _actual_counts(test_rows)
        rates = _baseline_rates(counts, n)
        test = fold.get("test") if isinstance(fold.get("test"), dict) else {}
        test_acc = float(test.get("accuracy") or 0.0)
        prod_control = float(test.get("always_bull_control") or rates["always_bull_test"] or 0.0)
        train_bull = float(fold.get("train_bull_fraction") or 0.0)
        margin_prod = round(test_acc - prod_control, 6)

        alt_controls = {
            "prod_always_bull_test": prod_control,
            "train_bull_fraction": round(train_bull, 6),
            **rates,
        }
        gt_under_alt = {k: _gt_pass(test_acc, v) for k, v in alt_controls.items()}

        fold_rows.append(
            {
                "fold_index": fi,
                "n_test_rows": n,
                "n_test_dates_requested": len(test_dates),
                "actual_counts": counts,
                "test_accuracy": round(test_acc, 6),
                "test_hits": test.get("hits"),
                "prod_always_bull_control": round(prod_control, 6),
                "margin_vs_prod_control": margin_prod,
                "exact_tie_with_prod_control": margin_prod == 0.0,
                "wf_test_beats_always_bull": fold.get("test_beats_always_bull"),
                "wf_test_meets_or_beats_always_bull": fold.get("test_meets_or_beats_always_bull"),
                "alternative_controls": alt_controls,
                "gt_pass_under_alt_control": gt_under_alt,
                "counterfactual_gt_pass_count": sum(1 for k, v in gt_under_alt.items() if k != "prod_always_bull_test" and v is True),
            }
        )

    n_folds = len(fold_rows)
    exact_ties = sum(1 for f in fold_rows if f.get("exact_tie_with_prod_control"))
    prod_gt_pass = sum(1 for f in fold_rows if f.get("gt_pass_under_alt_control", {}).get("prod_always_bull_test"))
    any_alt_gt = any((f.get("counterfactual_gt_pass_count") or 0) > 0 for f in fold_rows)

    verdict_ko = (
        f"prod always_bull=test bull fraction; {exact_ties}/{n_folds} fold exact tie (margin=0) → gt 0/{n_folds}. "
        "beat_bull_first가 fold별 always-bull hit rate에 맞춰져 structural degeneracy."
    )
    if any_alt_gt:
        verdict_ko += (
            " 일부 fold는 train_bull/majority 등 대체 control이면 gt 통과 counterfactual 가능하나 "
            "prod gate 정의 변경 없이는 승격 근거 아님."
        )
    else:
        verdict_ko += " 대체 baseline swap으로도 gt 통과 fold 없음."

    report: dict[str, Any] = {
        "schema": "prophecy_lens_always_bull_baseline_audit_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "track_a_auto_promote": False,
        "send_gate": "HOLD",
        "inputs": {
            "walkforward_json": _rel(args.walkforward_json),
            "score_json": _rel(args.score_json),
        },
        "prod_control_definition": (
            "always_bull_control = test-fold fraction of rows with actual_direction==bull "
            "(run_prophecy_per_date_combo_walkforward_v1.py)"
        ),
        "folds": fold_rows,
        "summary": {
            "n_folds": n_folds,
            "exact_tie_with_prod_control": exact_ties,
            "prod_gt_pass_folds": prod_gt_pass,
            "prod_gte_pass_folds": sum(
                1 for f in fold_rows if (f.get("test_accuracy") or 0) >= (f.get("prod_always_bull_control") or 0)
            ),
            "any_counterfactual_alt_control_gt_pass": any_alt_gt,
        },
        "verdict_ko": verdict_ko,
        "ledger_line": (
            f"Lens always_bull audit: {exact_ties}/{n_folds} folds exact tie prod control; "
            f"gt {prod_gt_pass}/{n_folds}; prod comparator unchanged; no oper promotion."
        ),
        "operator_lines": [
            "- [LENS-AUDIT] research_only; prod always_bull=test bull fraction.",
            f"- [LENS-AUDIT] exact_tie={exact_ties}/{n_folds} prod_gt_pass={prod_gt_pass}/{n_folds}.",
            f"- [LENS-AUDIT] {verdict_ko[:120]}…",
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
