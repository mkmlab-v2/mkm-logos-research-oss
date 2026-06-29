#!/usr/bin/env python3
"""Nested tune revalidate: sweep on pre-June train, score June prophecy holdout [HYPO]."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from itertools import product
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_kospi_field_band_cptc_lite_v1 import run_cptc_lite  # noqa: E402
from scripts.run_kospi_field_band_rwc_lite_v1 import run_rwc_lite  # noqa: E402
from scripts.run_kospi_field_band_stack_ensemble_v1 import run_stack_ensemble  # noqa: E402
from scripts.run_kospi_four_lens_conditional_fusion_ablation_v1 import _read  # noqa: E402
from scripts.run_kospi_four_lens_conflict_band_coverage_wf_v1 import _band_hit_rate  # noqa: E402

DEFAULT_EVAL = ROOT / "reports/kospi_multi_month_prophecy_eval_v1_latest.json"
DEFAULT_CAL = ROOT / "reports/kospi_multi_month_prophecy_calendar_v1_latest.json"
DEFAULT_FUSION = ROOT / "reports/kospi_four_lens_graphrag_fusion_v1_latest.json"
DEFAULT_FIELD_TIER2 = ROOT / "reports/field_lens_vol_band_tier2_v1_latest.json"
DEFAULT_POLICY = ROOT / "docs/final/artifacts/kospi_field_band_conformal_tuned_policy_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/kospi_field_band_nested_tune_revalidate_v1_latest.json"
ART_OUT = ROOT / "docs/final/artifacts/kospi_field_band_nested_tune_revalidate_v1_latest.json"

TRAIN_CUTOFF = "2026-06-01"
MIN_DELTA_PP = 0.03


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _prophecy_rows(eval_doc: dict[str, Any]) -> list[dict[str, Any]]:
    rows = eval_doc.get("rows") if isinstance(eval_doc.get("rows"), list) else []
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if row.get("backfill_source"):
            continue
        if row.get("actual_direction") not in ("bull", "bear", "neutral"):
            continue
        out.append(row)
    out.sort(key=lambda r: str(r.get("session_date") or ""))
    return out


def _date_sets(prophecy_rows: list[dict[str, Any]]) -> tuple[set[str], set[str]]:
    train: set[str] = set()
    holdout: set[str] = set()
    for row in prophecy_rows:
        dk = str(row.get("session_date"))
        if dk < TRAIN_CUTOFF:
            train.add(dk)
        else:
            holdout.add(dk)
    return train, holdout


def _rate_on_dates(daily: list[dict[str, Any]], dates: set[str], hit_key: str) -> float | None:
    sub = [r for r in daily if str(r.get("session_date")) in dates]
    if not sub:
        return None
    hits = [r.get(hit_key) for r in sub]
    return _band_hit_rate([h if isinstance(h, bool) else None for h in hits])


def _stack_doc_rates(stack_doc: dict[str, Any], dates: set[str]) -> dict[str, float | None]:
    daily = stack_doc.get("daily_rows") or []
    return {
        "base": _rate_on_dates(daily, dates, "band_hit_base"),
        "stack": _rate_on_dates(daily, dates, "band_hit_stack"),
    }


def run_nested_revalidate(
    eval_doc: dict[str, Any],
    calendar: dict[str, Any],
    fusion: dict[str, Any],
    *,
    field_tier2: dict[str, Any] | None = None,
    frozen_policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    prophecy = _prophecy_rows(eval_doc)
    train_dates, june_holdout_dates = _date_sets(prophecy)

    rwc_decay_grid = [0.03, 0.05, 0.08]
    rwc_gamma_grid = [0.12, 0.15, 0.18]
    cptc_vol_grid = [1.5, 1.75, 2.0]
    cptc_gamma_grid = [0.15, 0.18, 0.21]

    best_rwc_doc: dict[str, Any] | None = None
    best_rwc_rate = -1.0
    best_rwc_params: dict[str, float] = {"decay_lambda": 0.05, "margin_gamma": 0.15}

    for decay, gamma in product(rwc_decay_grid, rwc_gamma_grid):
        doc = run_rwc_lite(
            eval_doc,
            calendar,
            fusion,
            field_tier2=field_tier2,
            decay_lambda=decay,
            margin_gamma=gamma,
        )
        rate = _rate_on_dates(doc.get("daily_rows") or [], train_dates, "band_hit_rwc")
        if rate is not None and rate > best_rwc_rate:
            best_rwc_rate = rate
            best_rwc_doc = doc
            best_rwc_params = {"decay_lambda": decay, "margin_gamma": gamma, "bandwidth_h": 1.0}

    best_cptc_doc: dict[str, Any] | None = None
    best_cptc_rate = -1.0
    best_cptc_params: dict[str, float] = {"vol_jump_threshold": 1.75, "margin_gamma": 0.18, "base_quantile_q": 0.88}

    for vol_jump, gamma in product(cptc_vol_grid, cptc_gamma_grid):
        doc = run_cptc_lite(
            eval_doc,
            calendar,
            fusion,
            field_tier2=field_tier2,
            vol_jump_threshold=vol_jump,
            margin_gamma=gamma,
        )
        rate = _rate_on_dates(doc.get("daily_rows") or [], train_dates, "band_hit_cptc")
        if rate is not None and rate > best_cptc_rate:
            best_cptc_rate = rate
            best_cptc_doc = doc
            best_cptc_params = {
                "vol_jump_threshold": vol_jump,
                "margin_gamma": gamma,
                "base_quantile_q": 0.88,
            }

    assert best_rwc_doc and best_cptc_doc
    nested_stack = run_stack_ensemble(eval_doc, calendar, best_rwc_doc, best_cptc_doc)
    nested_june = _stack_doc_rates(nested_stack, june_holdout_dates)

    fp = frozen_policy or {}
    rwc_p = fp.get("rwc") if isinstance(fp.get("rwc"), dict) else {}
    cptc_p = fp.get("cptc") if isinstance(fp.get("cptc"), dict) else {}
    frozen_rwc = run_rwc_lite(
        eval_doc,
        calendar,
        fusion,
        field_tier2=field_tier2,
        decay_lambda=float(rwc_p.get("decay_lambda") or 0.08),
        margin_gamma=float(rwc_p.get("margin_gamma") or 0.18),
    )
    frozen_cptc = run_cptc_lite(
        eval_doc,
        calendar,
        fusion,
        field_tier2=field_tier2,
        vol_jump_threshold=float(cptc_p.get("vol_jump_threshold") or 1.75),
        margin_gamma=float(cptc_p.get("margin_gamma") or 0.18),
    )
    frozen_stack = run_stack_ensemble(eval_doc, calendar, frozen_rwc, frozen_cptc)
    frozen_june = _stack_doc_rates(frozen_stack, june_holdout_dates)

    nested_base = float(nested_june.get("base") or 0.0)
    nested_stack_rate = float(nested_june.get("stack") or 0.0)
    nested_delta = round(nested_stack_rate - nested_base, 4)

    frozen_base = float(frozen_june.get("base") or 0.0)
    frozen_stack_rate = float(frozen_june.get("stack") or 0.0)
    frozen_delta = round(frozen_stack_rate - frozen_base, 4)

    revalidation_pass = nested_delta >= MIN_DELTA_PP and len(june_holdout_dates) >= 10

    return {
        "schema": "kospi_field_band_nested_tune_revalidate_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "auto_apply": False,
        "send_gate": "HOLD",
        "protocol": "train_tune_pre_june_prophecy_score_june_prophecy_only",
        "train_cutoff": TRAIN_CUTOFF,
        "train_prophecy_n": len(train_dates),
        "june_holdout_prophecy_n": len(june_holdout_dates),
        "nested_best_params": {"rwc": best_rwc_params, "cptc": best_cptc_params},
        "june_holdout_metrics": {
            "nested_tune": {
                "band_base": nested_base,
                "band_stack_union": nested_stack_rate,
                "delta_stack_minus_base": nested_delta,
            },
            "frozen_pooled_holdout_policy": {
                "band_base": frozen_base,
                "band_stack_union": frozen_stack_rate,
                "delta_stack_minus_base": frozen_delta,
                "policy_pointer": "docs/final/artifacts/kospi_field_band_conformal_tuned_policy_v1_latest.json",
            },
        },
        "revalidation_pass": revalidation_pass,
        "verdict_ko": (
            "June prophecy holdout stack 개선 확인 — nested tune 연구 후보"
            if revalidation_pass
            else "June prophecy holdout 재검증 미달 — tuned 승격 주장 보류"
        ),
        "caveats_ko": [
            "May+June prophecy만 평가·Jan–Apr backfill 제외.",
            "Train tune은 May 구간 포함 — June 완전 누수는 아님.",
            "band_hit ≠ PnL.",
        ],
        "reproduce": "py scripts/run_kospi_field_band_nested_tune_revalidate_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--eval-json", type=Path, default=DEFAULT_EVAL)
    ap.add_argument("--calendar-json", type=Path, default=DEFAULT_CAL)
    ap.add_argument("--fusion-json", type=Path, default=DEFAULT_FUSION)
    ap.add_argument("--field-tier2-json", type=Path, default=DEFAULT_FIELD_TIER2)
    ap.add_argument("--policy-json", type=Path, default=DEFAULT_POLICY)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    ev = _read(args.eval_json)
    cal = _read(args.calendar_json)
    fusion = _read(args.fusion_json)
    if not ev or not cal or not fusion:
        print("Missing inputs", file=sys.stderr)
        return 2

    doc = run_nested_revalidate(
        ev,
        cal,
        fusion,
        field_tier2=_read(args.field_tier2_json),
        frozen_policy=_read(args.policy_json),
    )
    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(payload, encoding="utf-8")
    ART_OUT.parent.mkdir(parents=True, exist_ok=True)
    ART_OUT.write_text(payload, encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "revalidation_pass": doc["revalidation_pass"],
                "june_nested_delta": doc["june_holdout_metrics"]["nested_tune"]["delta_stack_minus_base"],
                "june_frozen_delta": doc["june_holdout_metrics"]["frozen_pooled_holdout_policy"]["delta_stack_minus_base"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
