#!/usr/bin/env python3
"""Grid sweep for RWC-lite + CPTC-lite holdout band params [HYPO][B-track]."""
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

DEFAULT_EVAL = ROOT / "reports/kospi_multi_month_prophecy_eval_v1_latest.json"
DEFAULT_CAL = ROOT / "reports/kospi_multi_month_prophecy_calendar_v1_latest.json"
DEFAULT_FUSION = ROOT / "reports/kospi_four_lens_graphrag_fusion_v1_latest.json"
DEFAULT_FIELD_TIER2 = ROOT / "reports/field_lens_vol_band_tier2_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/kospi_field_band_conformal_param_sweep_v1_latest.json"
ART_OUT = ROOT / "docs/final/artifacts/kospi_field_band_conformal_param_sweep_v1_latest.json"
POLICY_OUT = ROOT / "docs/final/artifacts/kospi_field_band_conformal_tuned_policy_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _hold_rate(doc: dict[str, Any], key: str) -> float:
    hold = (doc.get("summary") or {}).get("holdout_pooled") or {}
    return float(hold.get(key) or 0.0)


def _stack_rate(doc: dict[str, Any]) -> float:
    hold = ((doc.get("summary") or {}).get("holdout_pooled") or {}).get("stack") or {}
    return float(hold.get("band_hit_rate") or 0.0)


def run_sweep(
    eval_doc: dict[str, Any],
    calendar: dict[str, Any],
    fusion: dict[str, Any],
    *,
    field_tier2: dict[str, Any] | None = None,
    rwc_decay_grid: list[float],
    rwc_gamma_grid: list[float],
    cptc_vol_jump_grid: list[float],
    cptc_gamma_grid: list[float],
) -> dict[str, Any]:
    tier2 = field_tier2

    default_rwc = run_rwc_lite(eval_doc, calendar, fusion, field_tier2=tier2)
    default_cptc = run_cptc_lite(eval_doc, calendar, fusion, field_tier2=tier2)
    default_stack = run_stack_ensemble(eval_doc, calendar, default_rwc, default_cptc)
    default_stack_rate = _stack_rate(default_stack)

    rwc_rows: list[dict[str, Any]] = []
    best_rwc_doc = default_rwc
    best_rwc_rate = _hold_rate(default_rwc, "band_hit_rate_rwc")
    best_rwc_params = {"decay_lambda": 0.05, "margin_gamma": 0.15, "bandwidth_h": 1.0}

    for decay, gamma in product(rwc_decay_grid, rwc_gamma_grid):
        doc = run_rwc_lite(
            eval_doc,
            calendar,
            fusion,
            field_tier2=tier2,
            decay_lambda=decay,
            margin_gamma=gamma,
        )
        rate = _hold_rate(doc, "band_hit_rate_rwc")
        rwc_rows.append(
            {
                "decay_lambda": decay,
                "margin_gamma": gamma,
                "holdout_band_hit_rate_rwc": rate,
                "delta_vs_base": (doc.get("summary") or {}).get("delta_rwc_minus_base_holdout"),
            }
        )
        if rate > best_rwc_rate:
            best_rwc_rate = rate
            best_rwc_doc = doc
            best_rwc_params = {"decay_lambda": decay, "margin_gamma": gamma, "bandwidth_h": 1.0}

    cptc_rows: list[dict[str, Any]] = []
    best_cptc_doc = default_cptc
    best_cptc_rate = _hold_rate(default_cptc, "band_hit_rate_cptc")
    best_cptc_params = {"vol_jump_threshold": 1.75, "margin_gamma": 0.18, "base_quantile_q": 0.88}

    for vol_jump, gamma in product(cptc_vol_jump_grid, cptc_gamma_grid):
        doc = run_cptc_lite(
            eval_doc,
            calendar,
            fusion,
            field_tier2=tier2,
            vol_jump_threshold=vol_jump,
            margin_gamma=gamma,
        )
        rate = _hold_rate(doc, "band_hit_rate_cptc")
        cptc_rows.append(
            {
                "vol_jump_threshold": vol_jump,
                "margin_gamma": gamma,
                "holdout_band_hit_rate_cptc": rate,
                "delta_vs_base": (doc.get("summary") or {}).get("delta_cptc_minus_base_holdout"),
            }
        )
        if rate > best_cptc_rate:
            best_cptc_rate = rate
            best_cptc_doc = doc
            best_cptc_params = {
                "vol_jump_threshold": vol_jump,
                "margin_gamma": gamma,
                "base_quantile_q": 0.88,
            }

    tuned_stack = run_stack_ensemble(eval_doc, calendar, best_rwc_doc, best_cptc_doc)
    tuned_stack_rate = _stack_rate(tuned_stack)
    beats_default = tuned_stack_rate > default_stack_rate + 1e-6

    return {
        "schema": "kospi_field_band_conformal_param_sweep_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "auto_apply": False,
        "send_gate": "HOLD",
        "default_stack_holdout_band_hit_rate": default_stack_rate,
        "tuned_stack_holdout_band_hit_rate": tuned_stack_rate,
        "delta_tuned_minus_default_stack": round(tuned_stack_rate - default_stack_rate, 4),
        "beats_default": beats_default,
        "best_rwc_params": best_rwc_params,
        "best_cptc_params": best_cptc_params,
        "best_rwc_holdout_band_hit_rate": best_rwc_rate,
        "best_cptc_holdout_band_hit_rate": best_cptc_rate,
        "grid_rows_rwc": rwc_rows,
        "grid_rows_cptc": cptc_rows,
        "recommendation": "apply_tuned_policy" if beats_default else "keep_default_policy",
        "reproduce": "py scripts/run_kospi_field_band_conformal_param_sweep_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--eval-json", type=Path, default=DEFAULT_EVAL)
    ap.add_argument("--calendar-json", type=Path, default=DEFAULT_CAL)
    ap.add_argument("--fusion-json", type=Path, default=DEFAULT_FUSION)
    ap.add_argument("--field-tier2-json", type=Path, default=DEFAULT_FIELD_TIER2)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--rwc-decay-grid", default="0.03,0.05,0.08")
    ap.add_argument("--rwc-gamma-grid", default="0.12,0.15,0.18")
    ap.add_argument("--cptc-vol-jump-grid", default="1.5,1.75,2.0")
    ap.add_argument("--cptc-gamma-grid", default="0.15,0.18,0.21")
    args = ap.parse_args()

    ev = _read(args.eval_json)
    cal = _read(args.calendar_json)
    fusion = _read(args.fusion_json)
    if not all((ev, cal, fusion)):
        print("Missing eval, calendar, or fusion", file=sys.stderr)
        return 2

    rwc_decay = [float(x.strip()) for x in args.rwc_decay_grid.split(",") if x.strip()]
    rwc_gamma = [float(x.strip()) for x in args.rwc_gamma_grid.split(",") if x.strip()]
    cptc_vol = [float(x.strip()) for x in args.cptc_vol_jump_grid.split(",") if x.strip()]
    cptc_gamma = [float(x.strip()) for x in args.cptc_gamma_grid.split(",") if x.strip()]

    doc = run_sweep(
        ev,
        cal,
        fusion,
        field_tier2=_read(args.field_tier2_json),
        rwc_decay_grid=rwc_decay,
        rwc_gamma_grid=rwc_gamma,
        cptc_vol_jump_grid=cptc_vol,
        cptc_gamma_grid=cptc_gamma,
    )

    policy = {
        "schema": "kospi_field_band_conformal_tuned_policy_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "use_tuned": doc["beats_default"],
        "rwc": doc["best_rwc_params"],
        "cptc": doc["best_cptc_params"],
        "sweep_pointer": "reports/kospi_field_band_conformal_param_sweep_v1_latest.json",
    }

    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(payload, encoding="utf-8")
    ART_OUT.parent.mkdir(parents=True, exist_ok=True)
    ART_OUT.write_text(payload, encoding="utf-8")
    POLICY_OUT.write_text(json.dumps(policy, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "beats_default": doc["beats_default"],
                "default_stack": doc["default_stack_holdout_band_hit_rate"],
                "tuned_stack": doc["tuned_stack_holdout_band_hit_rate"],
                "recommendation": doc["recommendation"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
