#!/usr/bin/env python3
"""[HYPO][NON_GATING] RQ-025 PoC: causal feature filter on flow + optional FRED join rows."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.rq025_causal_feature_filter_v1 import (  # noqa: E402
    SCHEMA,
    CausalFilterConfig,
    run_causal_feature_filter,
)

DEFAULT_FLOW_JOIN = ROOT / "reports/rq024_a_flow_eval_date_join_poc_v1_latest.json"
DEFAULT_FRED_JOIN = ROOT / "reports/btrack_session_panel_fred_lambda_join_252d_hypo_v1_latest.json"
DEFAULT_WIDE_JOIN = ROOT / "reports/rq025_flow_fred_wide_join_hypo_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/rq025_causal_feature_filter_poc_v1_latest.json"
DEFAULT_OUT_HYBRID = ROOT / "reports/rq025_causal_feature_filter_hybrid_252d_hypo_v1_latest.json"

FLOW_FEATURES = (
    "foreign_net_buy",
    "institution_net_buy",
    "program_net_buy",
    "individual_net_buy",
    "flow_score_monthly_rollup",
    "flow_score_single_day_proxy",
)
MACRO_FEATURES = ("lambda_t", "gradient", "z_score", "S", "L", "K", "M")
FEATURE_SET_KEYS = {
    "flow": list(FLOW_FEATURES),
    "macro": [f"macro_{k}" for k in MACRO_FEATURES],
    "all": list(FLOW_FEATURES) + [f"macro_{k}" for k in MACRO_FEATURES],
}
PROFILE_PRESETS: dict[str, dict[str, float]] = {
    "hybrid_relaxed": {"te_min": 0.0, "pcmci_min_abs_partial": 0.02},
    "flow_default": {"te_min": 0.5, "pcmci_min_abs_partial": 0.05},
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _fred_by_date(path: Path) -> dict[str, dict[str, Any]]:
    if not path.is_file():
        return {}
    doc = _load_json(path)
    out: dict[str, dict[str, Any]] = {}
    for row in doc.get("rows") or []:
        dk = str(row.get("session_local_date") or "")[:10]
        if len(dk) != 10:
            continue
        macro = row.get("macro") if row.get("macro_present") else None
        if isinstance(macro, dict):
            out[dk] = macro
    return out


def _build_matrix_from_wide_cohort(
    wide_doc: dict[str, Any],
    cohort: str,
    *,
    target: str,
    feature_keys: list[str] | None = None,
    require_intersection: bool = False,
    min_eval_date: str | None = None,
    max_eval_date: str | None = None,
) -> tuple[np.ndarray, list[str], np.ndarray, list[str]]:
    key = "rows_flow_panel_30d" if cohort == "flow_panel_30d" else "rows_hybrid_kospi_252d"
    source_rows = [r for r in wide_doc.get(key) or [] if isinstance(r, dict)]
    if require_intersection:
        source_rows = [
            r for r in source_rows if r.get("macro_present") and r.get("daily_flow_present")
        ]
    if min_eval_date or max_eval_date:
        lo = (min_eval_date or "")[:10]
        hi = (max_eval_date or "9999-12-31")[:10]
        source_rows = [
            r
            for r in source_rows
            if lo <= str(r.get("eval_date") or "")[:10] <= hi
        ]
    pseudo = {
        "rows": [
            {
                "eval_date": r.get("eval_date"),
                "panel_hit": r.get("panel_hit"),
                "predicted_direction": r.get("predicted_direction"),
                "actual_direction": r.get("actual_direction"),
                "daily_flow_present": r.get("daily_flow_present"),
                "daily_flow": r.get("daily_flow"),
                "flow_score_monthly_rollup": r.get("flow_score_monthly_rollup"),
                "flow_score_single_day_proxy": r.get("flow_score_single_day_proxy"),
                "foreign_flow_sign": r.get("foreign_flow_sign"),
            }
            for r in source_rows
        ]
    }
    fred_by_date: dict[str, dict[str, Any]] = {}
    for r in wide_doc.get(key) or []:
        if not isinstance(r, dict):
            continue
        dk = str(r.get("eval_date") or "")[:10]
        if r.get("macro_present") and isinstance(r.get("macro"), dict):
            fred_by_date[dk] = r["macro"]
    return _build_matrix_from_flow_join(
        pseudo, fred_by_date, target=target, feature_keys=feature_keys
    )


def _wide_cohort_intersection_count(wide_doc: dict[str, Any], cohort: str) -> int:
    key = "rows_flow_panel_30d" if cohort == "flow_panel_30d" else "rows_hybrid_kospi_252d"
    return sum(
        1
        for r in wide_doc.get(key) or []
        if isinstance(r, dict) and r.get("macro_present") and r.get("daily_flow_present")
    )


def _resolve_feature_keys(feature_set: str) -> list[str] | None:
    if feature_set not in FEATURE_SET_KEYS:
        raise ValueError(f"unknown feature_set: {feature_set}")
    if feature_set == "all":
        return None
    return list(FEATURE_SET_KEYS[feature_set])


def _build_matrix_from_flow_join(
    flow_doc: dict[str, Any],
    fred_by_date: dict[str, dict[str, Any]],
    *,
    target: str,
    feature_keys: list[str] | None = None,
) -> tuple[np.ndarray, list[str], np.ndarray, list[str]]:
    """Return X, feature_names, y, dates used."""
    rows_out: list[dict[str, float]] = []
    dates: list[str] = []
    y_vals: list[float] = []

    for row in flow_doc.get("rows") or []:
        dk = str(row.get("eval_date") or "")[:10]
        if len(dk) != 10:
            continue
        feat: dict[str, float] = {}
        daily = row.get("daily_flow") if row.get("daily_flow_present") else None
        if isinstance(daily, dict):
            for k in FLOW_FEATURES[:4]:
                try:
                    feat[k] = float(daily.get(k))
                except (TypeError, ValueError):
                    pass
        for k in FLOW_FEATURES[4:]:
            try:
                v = row.get(k)
                if v is not None:
                    feat[k] = float(v)
            except (TypeError, ValueError):
                pass
        macro = fred_by_date.get(dk)
        if isinstance(macro, dict):
            for k in MACRO_FEATURES:
                try:
                    v = macro.get(k)
                    if v is not None:
                        feat[f"macro_{k}"] = float(v)
                except (TypeError, ValueError):
                    pass

        if feature_keys is not None:
            keys = feature_keys
            if not all(k in feat and np.isfinite(feat[k]) for k in keys):
                continue
        else:
            keys = sorted(k for k, v in feat.items() if np.isfinite(v))
            if len(keys) < 2:
                continue

        if target == "panel_hit":
            hit = row.get("panel_hit")
            if hit is None:
                continue
            yv = 1.0 if bool(hit) else 0.0
        elif target == "foreign_sign_match":
            pred = str(row.get("foreign_flow_sign") or "").lower()
            actual = str(row.get("actual_direction") or "").lower()
            if pred not in {"bull", "bear", "neutral"}:
                continue
            yv = 1.0 if pred == actual else 0.0
        else:
            raise ValueError(f"unknown target: {target}")

        row_vec = {k: feat[k] for k in keys}
        rows_out.append(row_vec)
        dates.append(dk)
        y_vals.append(yv)

    if not rows_out:
        return np.empty((0, 0)), [], np.array([]), []

    all_keys = feature_keys if feature_keys is not None else sorted({k for r in rows_out for k in r})
    mat = np.array([[r.get(k, np.nan) for k in all_keys] for r in rows_out], dtype=float)
    y = np.array(y_vals, dtype=float)
    if feature_keys is None:
        mask = np.isfinite(mat).all(axis=1)
        mat = mat[mask]
        y = y[mask]
        dates = [d for d, keep in zip(dates, mask) if keep]
    return mat, all_keys, y, dates


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--flow-join-json", type=Path, default=DEFAULT_FLOW_JOIN)
    ap.add_argument("--fred-join-json", type=Path, default=DEFAULT_FRED_JOIN)
    ap.add_argument("--wide-join-json", type=Path, default=None)
    ap.add_argument(
        "--cohort",
        choices=("flow_panel_30d", "hybrid_kospi_252d"),
        default="flow_panel_30d",
    )
    ap.add_argument(
        "--require-intersection",
        action="store_true",
        help="Wide cohort: only rows with both macro_present and daily_flow_present",
    )
    ap.add_argument("--target", choices=("panel_hit", "foreign_sign_match"), default="panel_hit")
    ap.add_argument(
        "--feature-set",
        choices=tuple(FEATURE_SET_KEYS),
        default="all",
        help="Feature columns for matrix (hybrid macro-only avoids sparse-flow NaN drop)",
    )
    ap.add_argument(
        "--profile",
        choices=tuple(PROFILE_PRESETS),
        default=None,
        help="Threshold preset (hybrid_relaxed: te_min=0, pcmci=0.02)",
    )
    ap.add_argument("--corr-threshold", type=float, default=0.85)
    ap.add_argument("--te-min", type=float, default=None)
    ap.add_argument("--pcmci-min-abs-partial", type=float, default=None)
    ap.add_argument("--min-eval-date", default=None, help="Wide cohort: inclusive lower eval_date bound")
    ap.add_argument("--max-eval-date", default=None, help="Wide cohort: inclusive upper eval_date bound")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    preset = PROFILE_PRESETS.get(args.profile or "", {})
    te_min = float(args.te_min if args.te_min is not None else preset.get("te_min", 0.5))
    pcmci_min = float(
        args.pcmci_min_abs_partial
        if args.pcmci_min_abs_partial is not None
        else preset.get("pcmci_min_abs_partial", 0.05)
    )
    feature_keys: list[str] | None = _resolve_feature_keys(args.feature_set)

    flow_path = args.flow_join_json if args.flow_join_json.is_absolute() else ROOT / args.flow_join_json
    fred_path = args.fred_join_json if args.fred_join_json.is_absolute() else ROOT / args.fred_join_json
    out_path = args.output if args.output.is_absolute() else ROOT / args.output

    if args.wide_join_json:
        wide_path = args.wide_join_json if args.wide_join_json.is_absolute() else ROOT / args.wide_join_json
        if not wide_path.is_file():
            raise SystemExit(f"missing wide join: {wide_path}")
        wide_doc = _load_json(wide_path)
        x, names, y, dates = _build_matrix_from_wide_cohort(
            wide_doc,
            args.cohort,
            target=args.target,
            feature_keys=feature_keys,
            require_intersection=args.require_intersection,
            min_eval_date=args.min_eval_date,
            max_eval_date=args.max_eval_date,
        )
        flow_path = wide_path
        fred_path = wide_path
    else:
        if not flow_path.is_file():
            raise SystemExit(f"missing flow join: {flow_path}")
        flow_doc = _load_json(flow_path)
        fred_by_date = _fred_by_date(fred_path)
        x, names, y, dates = _build_matrix_from_flow_join(
            flow_doc, fred_by_date, target=args.target, feature_keys=feature_keys
        )

    cfg = CausalFilterConfig(
        corr_threshold=args.corr_threshold,
        te_min=te_min,
        pcmci_min_abs_partial=pcmci_min,
    )
    result = run_causal_feature_filter(x, names, y, cfg)

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "gating": "[NON_GATING]",
        "hypothesis_tag": "[HYPO]",
        "rq_id": "RQ-025",
        "inputs": {
            "flow_join_json": str(flow_path.relative_to(ROOT)).replace("\\", "/"),
            "fred_join_json": str(fred_path.relative_to(ROOT)).replace("\\", "/") if fred_path.is_file() else None,
            "wide_join_json": str((args.wide_join_json or Path()).as_posix()) if args.wide_join_json else None,
            "cohort": args.cohort,
            "target": args.target,
            "feature_set": args.feature_set,
            "profile": args.profile,
            "require_intersection": args.require_intersection,
            "min_eval_date": args.min_eval_date,
            "max_eval_date": args.max_eval_date,
            "intersection_rows_in_wide": (
                _wide_cohort_intersection_count(wide_doc, args.cohort)
                if args.wide_join_json
                else None
            ),
            "n_rows": int(x.shape[0]),
            "n_features_in": len(names),
            "date_min": min(dates) if dates else None,
            "date_max": max(dates) if dates else None,
        },
        "selected_features": result.selected_features,
        "dropped_correlation": result.dropped,
        "stages": result.stages,
        "track_wall": {
            "track_a_auto_merge": False,
            "oracle_promotion": False,
            "live_trading": False,
        },
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path} selected={len(result.selected_features)} n_rows={x.shape[0]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
