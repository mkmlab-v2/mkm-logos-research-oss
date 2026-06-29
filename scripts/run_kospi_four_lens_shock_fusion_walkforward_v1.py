#!/usr/bin/env python3
"""Shock-day-only 4-lens fusion blocked walk-forward over June KOSPI eval [HYPO]."""
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

from scripts.eval_kospi_june2026_daily_prophecy_v1 import _outcome  # noqa: E402
from scripts.run_kospi_four_lens_conditional_fusion_ablation_v1 import (  # noqa: E402
    _fusion_adjusted_direction,
    _read,
)
from scripts.run_kospi_four_lens_shock_conditional_ablation_v1 import (  # noqa: E402
    _is_shock_day,
    _soft_score,
    PRIOR_SHOCK_PCT,
    SHOCK_RETURN_PCT,
)

DEFAULT_EVAL = ROOT / "reports/kospi_june2026_daily_prophecy_eval_latest.json"
DEFAULT_FUSION = ROOT / "reports/kospi_four_lens_graphrag_fusion_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/kospi_four_lens_shock_fusion_walkforward_v1_latest.json"
ART_OUT = ROOT / "docs/final/artifacts/kospi_four_lens_shock_fusion_walkforward_v1_latest.json"
DEFAULT_MD = ROOT / "reports/kospi_four_lens_shock_fusion_walkforward_v1_latest.md"

ARM_IDS = ("active", "fusion_always", "fusion_shock_only", "fusion_shock_conflict_penalty")


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _scored_rows(eval_doc: dict[str, Any]) -> list[dict[str, Any]]:
    rows = eval_doc.get("rows")
    if not isinstance(rows, list):
        return []
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if row.get("actual_direction") not in ("bull", "bear", "neutral"):
            continue
        out.append(row)
    out.sort(key=lambda r: str(r.get("session_date") or ""))
    return out


def blocked_folds(dates: list[str], n_folds: int) -> list[tuple[list[str], list[str]]]:
    """Blocked expanding train / single-block test folds (test-only scoring)."""
    n = len(dates)
    if n_folds < 2 or n < n_folds:
        return []
    base = n // n_folds
    rem = n % n_folds
    blocks: list[list[str]] = []
    idx = 0
    for b in range(n_folds):
        sz = base + (1 if b < rem else 0)
        blocks.append(dates[idx : idx + sz])
        idx += sz
    folds: list[tuple[list[str], list[str]]] = []
    for f in range(1, n_folds):
        train: list[str] = []
        for b in range(f):
            train.extend(blocks[b])
        test = blocks[f]
        if train and test:
            folds.append((train, test))
    return folds


def _predict_for_row(
    row: dict[str, Any],
    fusion: dict[str, Any],
    *,
    mode: str,
    shock_return_pct: float,
    prior_shock_pct: float,
) -> str:
    pred_active = str(row.get("predicted_direction"))
    if mode == "active":
        return pred_active
    if mode == "fusion_always":
        return _fusion_adjusted_direction(fusion, pred_active)
    if mode == "fusion_shock_only":
        shock = _is_shock_day(row, shock_return_pct=shock_return_pct, prior_shock_pct=prior_shock_pct)
        return _fusion_adjusted_direction(fusion, pred_active) if shock else pred_active
    if mode == "fusion_shock_conflict_penalty":
        shock = _is_shock_day(row, shock_return_pct=shock_return_pct, prior_shock_pct=prior_shock_pct)
        if not shock:
            return pred_active
        pred = _fusion_adjusted_direction(fusion, pred_active)
        # DISCOUQ-lite: conflict-day weak-disagreement uses neutral to avoid overconfident flips.
        if _needs_conflict_penalty(fusion=fusion, active_pred=pred_active, fused_pred=pred):
            return "neutral"
        return pred
    return pred_active


def _needs_conflict_penalty(*, fusion: dict[str, Any], active_pred: str, fused_pred: str) -> bool:
    res = fusion.get("fusion_resolution") or {}
    conflicts = set(res.get("conflict_ids") or [])
    field = fusion.get("field") or {}
    logos = (fusion.get("lenses") or {}).get("logos") or {}
    field_sign = str(field.get("direction_sign") or "")
    logos_sign = str(logos.get("direction_sign") or "")
    active = str(active_pred or "")
    fused = str(fused_pred or "")
    weak_disagreement = (
        active not in ("", "neutral")
        and fused not in ("", "neutral")
        and active != fused
        and "field_bear_vs_lens_bull_majority" in conflicts
    )
    agreement_bias = field_sign == logos_sign and field_sign in ("bull", "bear")
    return weak_disagreement and agreement_bias


def _arm_outcomes_on_rows(
    rows: list[dict[str, Any]],
    fusion: dict[str, Any],
    *,
    mode: str,
    shock_return_pct: float,
    prior_shock_pct: float,
) -> list[str]:
    outcomes: list[str] = []
    for row in rows:
        actual = str(row.get("actual_direction"))
        pred = _predict_for_row(
            row,
            fusion,
            mode=mode,
            shock_return_pct=shock_return_pct,
            prior_shock_pct=prior_shock_pct,
        )
        outcomes.append(_outcome(pred, actual))
    return outcomes


def _arm_summary(outcomes: list[str], *, shock_days: int | None = None) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "n_scored": len(outcomes),
        "soft_hit_rate": _soft_score(outcomes),
    }
    if shock_days is not None:
        doc["shock_days"] = shock_days
    return doc


def run_shock_fusion_walkforward(
    eval_doc: dict[str, Any],
    fusion: dict[str, Any],
    *,
    n_folds: int = 4,
    shock_return_pct: float = SHOCK_RETURN_PCT,
    prior_shock_pct: float = PRIOR_SHOCK_PCT,
    min_holdout_n: int = 10,
    min_delta_pp: float = 0.03,
) -> dict[str, Any]:
    rows = _scored_rows(eval_doc)
    dates = [str(r["session_date"]) for r in rows]
    row_by_date = {str(r["session_date"]): r for r in rows}
    folds = blocked_folds(dates, n_folds)

    holdout_outcomes: dict[str, list[str]] = {aid: [] for aid in ARM_IDS}
    fold_docs: list[dict[str, Any]] = []

    for fi, (train, test) in enumerate(folds):
        test_rows = [row_by_date[d] for d in test]
        shock_days = sum(
            1
            for r in test_rows
            if _is_shock_day(r, shock_return_pct=shock_return_pct, prior_shock_pct=prior_shock_pct)
        )
        arms: dict[str, Any] = {}
        for mode in ARM_IDS:
            outcomes = _arm_outcomes_on_rows(
                test_rows,
                fusion,
                mode=mode,
                shock_return_pct=shock_return_pct,
                prior_shock_pct=prior_shock_pct,
            )
            holdout_outcomes[mode].extend(outcomes)
            arms[mode] = _arm_summary(
                outcomes,
                shock_days=shock_days if mode == "fusion_shock_only" else None,
            )
        fold_docs.append(
            {
                "fold": fi,
                "protocol": "blocked_expanding_train_test_only",
                "train_window": {"date_from": train[0], "date_to": train[-1], "n_days": len(train)},
                "test_window": {"date_from": test[0], "date_to": test[-1], "n_days": len(test)},
                "arms": arms,
            }
        )

    holdout_pooled: dict[str, Any] = {}
    for mode in ARM_IDS:
        holdout_pooled[mode] = _arm_summary(holdout_outcomes[mode])

    active_soft = float(holdout_pooled["active"]["soft_hit_rate"])
    shock_soft = float(holdout_pooled["fusion_shock_only"]["soft_hit_rate"])
    always_soft = float(holdout_pooled["fusion_always"]["soft_hit_rate"])
    penalty_soft = float(holdout_pooled["fusion_shock_conflict_penalty"]["soft_hit_rate"])
    n_holdout = int(holdout_pooled["fusion_shock_only"]["n_scored"])
    delta_shock = round(shock_soft - active_soft, 4)
    delta_always = round(always_soft - active_soft, 4)
    delta_penalty = round(penalty_soft - active_soft, 4)
    promotion_ready = delta_shock >= min_delta_pp and n_holdout >= min_holdout_n

    return {
        "schema": "kospi_four_lens_shock_fusion_walkforward_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "auto_apply": False,
        "track_wall": "no_track_a_live_auto_merge",
        "eval_pointer": "reports/kospi_june2026_daily_prophecy_eval_latest.json",
        "fusion_pointer": "reports/kospi_four_lens_graphrag_fusion_v1_latest.json",
        "shock_thresholds": {
            "abs_return_pct": shock_return_pct,
            "prior_kospi_pct": prior_shock_pct,
        },
        "config": {
            "n_folds": n_folds,
            "protocol": "blocked_expanding_train_test_only",
            "min_holdout_n": min_holdout_n,
            "min_delta_pp": min_delta_pp,
        },
        "n_scored_total": len(rows),
        "folds": fold_docs,
        "holdout_pooled": holdout_pooled,
        "comparison": {
            "delta_shock_only_minus_active_holdout": delta_shock,
            "delta_always_minus_active_holdout": delta_always,
            "delta_conflict_penalty_minus_active_holdout": delta_penalty,
            "shock_only_beats_always_holdout": shock_soft > always_soft,
            "conflict_penalty_beats_shock_only_holdout": penalty_soft > shock_soft,
        },
        "promotion_ready": promotion_ready,
        "verdict_ko": (
            "holdout shock-only fusion이 active 대비 +3%p — WF 연구 후보"
            if promotion_ready
            else "holdout shock-only fusion 승격 미달 — 충돌·Field 앵커만 유지"
        ),
    }


def render_walkforward_md(doc: dict[str, Any]) -> str:
    hold = doc.get("holdout_pooled") or {}
    cmp_ = doc.get("comparison") or {}
    lines = [
        "> **[HYPO][research_only]** shock-day-only 4-lens fusion blocked walk-forward (June 2026 eval).",
        "",
        f"- folds: {len(doc.get('folds') or [])} · holdout n={((hold.get('active') or {}).get('n_scored'))}",
        f"- active holdout soft: {(hold.get('active') or {}).get('soft_hit_rate')}",
        f"- fusion_shock_only holdout soft: {(hold.get('fusion_shock_only') or {}).get('soft_hit_rate')}",
        f"- fusion_shock_conflict_penalty holdout soft: {(hold.get('fusion_shock_conflict_penalty') or {}).get('soft_hit_rate')}",
        f"- delta shock-only vs active: {cmp_.get('delta_shock_only_minus_active_holdout')}",
        f"- delta conflict-penalty vs active: {cmp_.get('delta_conflict_penalty_minus_active_holdout')}",
        f"- promotion_ready: `{doc.get('promotion_ready')}`",
        "",
        doc.get("verdict_ko") or "",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--eval-json", type=Path, default=DEFAULT_EVAL)
    ap.add_argument("--fusion-json", type=Path, default=DEFAULT_FUSION)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--out-md", type=Path, default=DEFAULT_MD)
    ap.add_argument("--n-folds", type=int, default=4)
    ap.add_argument("--shock-return-pct", type=float, default=SHOCK_RETURN_PCT)
    ap.add_argument("--prior-shock-pct", type=float, default=PRIOR_SHOCK_PCT)
    args = ap.parse_args()

    ev = _read(args.eval_json)
    fusion = _read(args.fusion_json)
    if not ev or not fusion:
        print("Missing eval or fusion", file=sys.stderr)
        return 2

    rows = _scored_rows(ev)
    if len(rows) < args.n_folds:
        print(f"Insufficient scored rows ({len(rows)}) for n_folds={args.n_folds}", file=sys.stderr)
        return 2

    doc = run_shock_fusion_walkforward(
        ev,
        fusion,
        n_folds=args.n_folds,
        shock_return_pct=args.shock_return_pct,
        prior_shock_pct=args.prior_shock_pct,
    )
    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(payload, encoding="utf-8")
    ART_OUT.parent.mkdir(parents=True, exist_ok=True)
    ART_OUT.write_text(payload, encoding="utf-8")
    args.out_md.write_text(render_walkforward_md(doc), encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "comparison": doc["comparison"],
                "promotion_ready": doc["promotion_ready"],
                "n_folds": len(doc.get("folds") or []),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
