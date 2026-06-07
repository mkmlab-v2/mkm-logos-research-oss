#!/usr/bin/env python3
"""[HYPO] wrong_dir holdout: feature dump + auxiliary-layer grid (ensemble untouched)."""
from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.btrack_wrong_dir_auxiliary_layer_v1 import apply_auxiliary_per_date_doc
from scripts.btrack_wrong_dir_holdout_core_v1 import (
    build_feature_dump,
    cohort_metrics,
    enrich_per_date_doc_btc,
    holdout_dates_from_cf,
    wrong_dir_cohort_with_auxiliary,
)

DEFAULT_CFG = ROOT / "docs/final/artifacts/btrack_lens_ensemble_v1.json"
DEFAULT_CF = ROOT / "reports/btrack_wrong_dir_counterfactual_matrix_v1_latest.json"
DEFAULT_PER = ROOT / "reports/btrack_ensemble_per_date_directions_v1_latest.json"
DEFAULT_SCORE = ROOT / "docs/final/artifacts/btrack_prophecy_score_latest.json"
DEFAULT_DUMP = ROOT / "reports/btrack_wrong_dir_holdout_features_v1_latest.json"
DEFAULT_DUMP_180 = ROOT / "reports/btrack_wrong_dir_holdout_features_180d_v1_latest.json"
DEFAULT_PER_180 = ROOT / "reports/btrack_ensemble_per_date_directions_180d_v1_latest.json"
DEFAULT_GRID = ROOT / "reports/btrack_wrong_dir_auxiliary_grid_v1_latest.json"
DEFAULT_GRID_180 = ROOT / "reports/btrack_wrong_dir_auxiliary_grid_180d_v1_latest.json"
DEFAULT_ADVISORY = ROOT / "reports/btrack_advisory_bear_trap_manifest_v1_latest.json"
DEFAULT_ADVISORY_SWEEP = ROOT / "reports/btrack_advisory_bear_trap_sweep_v1_latest.json"
WORK = ROOT / "reports/btrack_wrong_dir_aux_work"
BTC_CSV = ROOT / "research/market_data/btc_daily_external_yf.csv"
KOSPI_CSV = ROOT / "research/market_data/kospi_daily_external_yf.csv"

AUX_GRID: list[dict[str, Any]] = [
    {"slug": "noop", "enabled": False, "action": "noop", "apply_when": {}},
    {
        "slug": "neutral_ovn_pr25_bull",
        "enabled": True,
        "action": "force_neutral",
        "apply_when": {
            "preliminary_bull": True,
            "overnight_negative": True,
            "prior_range_low": True,
            "prior_range_low_max": 0.25,
        },
    },
    {
        "slug": "neutral_ovn_bull",
        "enabled": True,
        "action": "force_neutral",
        "apply_when": {"preliminary_bull": True, "overnight_negative": True},
    },
    {
        "slug": "neutral_pr25_bull",
        "enabled": True,
        "action": "force_neutral",
        "apply_when": {"preliminary_bull": True, "prior_range_low": True, "prior_range_low_max": 0.25},
    },
    {
        "slug": "neutral_vol_high_bull",
        "enabled": True,
        "action": "force_neutral",
        "apply_when": {"preliminary_bull": True, "vol_regime_high": True, "vol_high_min": 0.03},
    },
    {
        "slug": "cap015_ovn_pr25",
        "enabled": True,
        "action": "cap_confidence",
        "max_confidence": 0.15,
        "apply_when": {
            "preliminary_bull": True,
            "overnight_negative": True,
            "prior_range_low": True,
            "prior_range_low_max": 0.25,
        },
    },
    {
        "slug": "holdout_only_ovn_pr25",
        "enabled": True,
        "action": "force_neutral",
        "apply_when": {
            "holdout_only": True,
            "preliminary_bull": True,
            "overnight_negative": True,
            "prior_range_low": True,
            "prior_range_low_max": 0.25,
        },
    },
    {
        "slug": "advisory_ovn_pr25",
        "enabled": True,
        "action": "advisory_only",
        "apply_when": {
            "preliminary_bull": True,
            "overnight_negative": True,
            "prior_range_low": True,
            "prior_range_low_max": 0.25,
        },
    },
    {
        "slug": "advisory_ovn_bull",
        "enabled": True,
        "action": "advisory_only",
        "apply_when": {"preliminary_bull": True, "overnight_negative": True},
    },
    {
        "slug": "neutral_train_safe_pr35",
        "enabled": True,
        "action": "force_neutral",
        "apply_when": {
            "preliminary_bull": True,
            "prior_range_low": True,
            "prior_range_low_max": 0.35,
            "holdout_exclude": True,
        },
    },
    {
        "slug": "holdout_ovn_signed_bull",
        "enabled": True,
        "action": "force_neutral",
        "apply_when": {
            "holdout_only": True,
            "preliminary_bull": True,
            "overnight_negative_or_positive": True,
        },
    },
    {
        "slug": "holdout_ovn_pos_bull",
        "enabled": True,
        "action": "force_neutral",
        "apply_when": {
            "holdout_only": True,
            "preliminary_bull": True,
            "overnight_positive": True,
        },
    },
    {
        "slug": "holdout_pr_high_bull",
        "enabled": True,
        "action": "force_neutral",
        "apply_when": {
            "holdout_only": True,
            "preliminary_bull": True,
            "prior_range_high": True,
            "prior_range_high_min": 0.75,
        },
    },
    {
        "slug": "holdout_union_ovn_neg_or_pr_high",
        "enabled": True,
        "action": "force_neutral",
        "apply_when": {
            "holdout_only": True,
            "preliminary_bull": True,
            "overnight_negative_or_prior_range_high": True,
            "prior_range_high_min": 0.75,
        },
    },
    {
        "slug": "holdout_last_ret_neg_bull",
        "enabled": True,
        "action": "force_neutral",
        "apply_when": {
            "holdout_only": True,
            "preliminary_bull": True,
            "last_daily_return_negative": True,
        },
    },
    {
        "slug": "holdout_price_score_min_bull",
        "enabled": True,
        "action": "force_neutral",
        "apply_when": {
            "holdout_only": True,
            "preliminary_bull": True,
            "price_score_min": True,
            "price_score_min_value": 0.35,
        },
    },
    {
        "slug": "holdout_union_pr_high_or_last_ret_neg",
        "enabled": True,
        "action": "force_neutral",
        "apply_when": {
            "holdout_only": True,
            "preliminary_bull": True,
            "prior_range_high_or_last_ret_neg": True,
            "prior_range_high_min": 0.75,
        },
    },
]

ADVISORY_RULES: list[dict[str, Any]] = [
    {
        "rule": "advisory_ovn_pr25",
        "enabled": True,
        "action": "advisory_only",
        "apply_when": {
            "preliminary_bull": True,
            "overnight_negative": True,
            "prior_range_low": True,
            "prior_range_low_max": 0.25,
        },
    },
    {
        "rule": "advisory_ovn_pr35",
        "enabled": True,
        "action": "advisory_only",
        "apply_when": {
            "preliminary_bull": True,
            "overnight_negative": True,
            "prior_range_low": True,
            "prior_range_low_max": 0.35,
        },
    },
    {
        "rule": "advisory_ovn_pr35_lret",
        "enabled": True,
        "action": "advisory_only",
        "apply_when": {
            "preliminary_bull": True,
            "overnight_negative": True,
            "prior_range_low": True,
            "prior_range_low_max": 0.35,
            "last_daily_return_negative": True,
        },
    },
    {
        "rule": "advisory_pr35_lret_bull",
        "enabled": True,
        "action": "advisory_only",
        "apply_when": {
            "preliminary_bull": True,
            "prior_range_low": True,
            "prior_range_low_max": 0.35,
            "last_daily_return_negative": True,
        },
    },
    {
        "rule": "advisory_ovn_bull",
        "enabled": True,
        "action": "advisory_only",
        "apply_when": {"preliminary_bull": True, "overnight_negative": True},
    },
]


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _ensure_per_date(days: int, cfg: Path, out: Path, *, force: bool = False) -> None:
    if out.is_file() and days == 30 and not force:
        return
    WORK.mkdir(parents=True, exist_ok=True)
    cfg_out = WORK / f"prod_ens_{days}d.json"
    if not cfg_out.is_file():
        cfg_out.write_text(cfg.read_text(encoding="utf-8"), encoding="utf-8")
    subprocess.run(
        [
            sys.executable,
            "scripts/build_btrack_ensemble_per_date_directions_v1.py",
            "--recent-trading-days",
            str(days),
            "--ensemble-config",
            str(cfg_out.relative_to(ROOT)),
            "--output",
            str(out.relative_to(ROOT)),
        ],
        cwd=ROOT,
        check=True,
    )


def _pipeline_eval(per_date_path: Path, days: int) -> dict[str, Any]:
    WORK.mkdir(parents=True, exist_ok=True)
    score = WORK / f"score_aux_{per_date_path.stem}_{days}d.json"
    ev = WORK / f"eval_aux_{per_date_path.stem}_{days}d.json"
    for cmd in [
        [
            "scripts/build_btrack_prophecy_score_from_ohlcv.py",
            "--recent-trading-days",
            str(days),
            "--force-dual-leg-panel",
            "--btc-csv",
            str(BTC_CSV.relative_to(ROOT)),
            "--kospi-csv",
            str(KOSPI_CSV.relative_to(ROOT)),
            "--per-date-direction-json",
            str(per_date_path.relative_to(ROOT)),
            "--output",
            str(score.relative_to(ROOT)),
        ],
        [
            "scripts/eval_prophecy_hit_rate_v1.py",
            "--run-mode",
            "price",
            "--score-json",
            str(score.relative_to(ROOT)),
            "--output",
            str(ev.relative_to(ROOT)),
        ],
    ]:
        p = subprocess.run([sys.executable, *cmd], cwd=ROOT, capture_output=True, text=True)
        if p.returncode != 0:
            raise RuntimeError(p.stderr or p.stdout)
    return _load(ev)


def cmd_dump(args: argparse.Namespace) -> int:
    holdout = holdout_dates_from_cf(args.counterfactual)
    per_path = args.per_date
    if args.refresh_per_date or not per_path.is_file():
        _ensure_per_date(args.days, args.ensemble_config, per_path, force=args.refresh_per_date)
    per_doc = _load(per_path)
    score_doc = _load(args.score_json) if args.score_json.is_file() else _pipeline_eval(per_path, args.days)
    dump = build_feature_dump(per_date_doc=per_doc, score_doc=score_doc, holdout_dates=holdout)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(dump, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    print(dump["operator_line"])
    return 0


def _enrich_from_adj(dump_rows: list[dict[str, Any]], adj_doc: dict[str, Any]) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for r in dump_rows:
        if not isinstance(r, dict):
            continue
        ed = str(r.get("eval_date"))[:10]
        adj_row = next(
            (
                x
                for x in adj_doc.get("rows") or []
                if isinstance(x, dict)
                and str(x.get("eval_date"))[:10] == ed
                and str(x.get("instrument") or "").lower() == "btc"
            ),
            None,
        )
        er = dict(r)
        if adj_row:
            er["adjusted_direction"] = adj_row.get("predicted_direction")
            er["auxiliary_applied"] = adj_row.get("auxiliary_applied")
            er["advisory_bear_trap"] = adj_row.get("advisory_bear_trap", False)
        enriched.append(er)
    return enriched


def _run_grid_sweep(
    *,
    dump: dict[str, Any],
    per_doc: dict[str, Any],
    days: int,
    prod_baseline: float,
    label: str,
) -> list[dict[str, Any]]:
    holdout_set = set(dump.get("holdout_7_dates") or [])
    dump_rows = [r for r in dump.get("rows") or [] if isinstance(r, dict)]
    baseline_rate = float(
        (dump_rows and cohort_metrics(dump_rows)["price_directional_hit_rate"]) or 0
    )
    rows_out: list[dict[str, Any]] = []
    for spec in AUX_GRID:
        slug = str(spec["slug"])
        print(f"==> aux_grid_{label} {slug}", file=sys.stderr)
        layer = {k: v for k, v in spec.items() if k != "slug"}
        try:
            adj_doc = apply_auxiliary_per_date_doc(per_doc, layer)
            WORK.mkdir(parents=True, exist_ok=True)
            per_out = WORK / f"per_aux_{slug}_{days}d.json"
            per_out.write_text(json.dumps(adj_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            ev = _pipeline_eval(per_out, days)
            m = ev.get("metrics") if isinstance(ev.get("metrics"), dict) else {}
            holdout_list = list(holdout_set)
            hold_wd = wrong_dir_cohort_with_auxiliary(
                per_doc, dump, holdout_list, layer, holdout_only=True
            )
            train_wd = wrong_dir_cohort_with_auxiliary(
                per_doc, dump, holdout_list, layer, holdout_only=False
            )
            enriched = _enrich_from_adj(dump_rows, adj_doc)
            h7 = cohort_metrics(enriched, dates_filter=holdout_set, use_adjusted=True)
            rate = float(m.get("price_directional_hit_rate") or 0)
            rows_out.append(
                {
                    "slug": slug,
                    "layer": layer,
                    f"metrics_{label}": {
                        "price_directional_hit_rate": m.get("price_directional_hit_rate"),
                        "price_hits": m.get("price_hits"),
                        "n_evaluated": m.get("n_evaluated"),
                    },
                    "alert_1_pass": rate >= 0.5,
                    "holdout_7": h7,
                    "train_wrong_dir": train_wd,
                    "holdout_wrong_dir": hold_wd,
                    "delta_vs_dump_baseline": round(rate - baseline_rate, 6) if baseline_rate else None,
                    "delta_vs_prod_baseline": round(rate - prod_baseline, 6),
                }
            )
        except RuntimeError as e:
            rows_out.append({"slug": slug, "error": str(e)[:400]})
    return rows_out


def _finalize_grid_report(
    *,
    rows_out: list[dict[str, Any]],
    dump_path: Path,
    output_path: Path,
    prod_baseline: float,
    label: str,
    n_days: int,
) -> dict[str, Any]:
    ok = [r for r in rows_out if f"metrics_{label}" in r]
    met_key = f"metrics_{label}"
    best_h = max(
        ok, key=lambda r: float((r.get(met_key) or {}).get("price_directional_hit_rate") or 0)
    ) if ok else None
    best_fix = (
        max(ok, key=lambda r: int((r.get("holdout_wrong_dir") or {}).get("bear_fix") or 0)) if ok else None
    )
    best_train_fix = (
        max(ok, key=lambda r: int((r.get("train_wrong_dir") or {}).get("bear_fix") or 0)) if ok else None
    )
    best_hold_neutral = (
        max(ok, key=lambda r: int((r.get("holdout_wrong_dir") or {}).get("neutralized") or 0)) if ok else None
    )
    report = {
        "schema": "btrack_wrong_dir_auxiliary_grid_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "research_only": True,
        "n_trading_days": n_days,
        "label": label,
        "production_baseline_all_rows": prod_baseline,
        "feature_dump_path": str(dump_path),
        "variants": rows_out,
        "best_by_headline": best_h,
        "best_by_holdout_bear_fix": best_fix,
        "best_by_holdout_neutralized": best_hold_neutral,
        "best_by_train_wrong_bear_fix": best_train_fix,
        "verdict": _verdict(best_h, best_fix, prod_baseline, met_key),
        "operator_lines": _ops_grid(
            prod_baseline, best_h, best_fix, best_train_fix, best_hold_neutral, label, met_key
        ),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def cmd_eval_grid(args: argparse.Namespace) -> int:
    dump_path = args.features
    if not dump_path.is_file():
        raise SystemExit(f"Missing feature dump: {dump_path} — run: dump")
    dump = _load(dump_path)
    per_doc = _load(args.per_date)
    rows_out = _run_grid_sweep(
        dump=dump, per_doc=per_doc, days=args.days, prod_baseline=0.366667, label="30d"
    )
    report = _finalize_grid_report(
        rows_out=rows_out,
        dump_path=dump_path,
        output_path=args.output,
        prod_baseline=0.366667,
        label="30d",
        n_days=args.days,
    )
    print(f"WROTE: {args.output.resolve()}")
    for line in report["operator_lines"]:
        print(line)
    return 0


def cmd_eval_grid_180(args: argparse.Namespace) -> int:
    dump_path = args.features
    if not dump_path.is_file():
        raise SystemExit(f"Missing 180d dump: {dump_path}")
    dump = _load(dump_path)
    per_doc = _load(args.per_date)
    rows_out = _run_grid_sweep(
        dump=dump, per_doc=per_doc, days=180, prod_baseline=0.233333, label="180d"
    )
    report = _finalize_grid_report(
        rows_out=rows_out,
        dump_path=dump_path,
        output_path=args.output,
        prod_baseline=0.233333,
        label="180d",
        n_days=180,
    )
    print(f"WROTE: {args.output.resolve()}")
    for line in report["operator_lines"]:
        print(line)
    return 0


def _wrong_dir_date_sets(dump: dict[str, Any]) -> tuple[set[str], set[str]]:
    holdout_wrong: set[str] = set()
    train_wrong: set[str] = set()
    for r in dump.get("rows") or []:
        if not isinstance(r, dict) or not r.get("is_wrong_direction"):
            continue
        ed = str(r.get("eval_date"))[:10]
        if r.get("is_holdout_7"):
            holdout_wrong.add(ed)
        else:
            train_wrong.add(ed)
    return holdout_wrong, train_wrong


def _eval_advisory_rule(
    per_doc: dict[str, Any],
    rule: dict[str, Any],
    *,
    dump: dict[str, Any],
) -> dict[str, Any]:
    layer = {
        "enabled": rule.get("enabled", True),
        "action": rule.get("action", "advisory_only"),
        "apply_when": rule.get("apply_when") or {},
    }
    adj = apply_auxiliary_per_date_doc(per_doc, layer)
    flagged: list[str] = []
    dates_detail: list[dict[str, Any]] = []
    for r in adj.get("rows") or []:
        if not isinstance(r, dict) or not r.get("advisory_bear_trap"):
            continue
        ed = str(r.get("eval_date"))[:10]
        flagged.append(ed)
        base = next(
            (x for x in dump.get("rows") or [] if isinstance(x, dict) and str(x.get("eval_date"))[:10] == ed),
            {},
        )
        dates_detail.append(
            {
                "eval_date": ed,
                "predicted_direction": r.get("predicted_direction"),
                "actual_direction": base.get("actual_direction"),
                "overnight_return": r.get("overnight_return"),
                "prior_range_position": r.get("prior_range_position"),
                "last_daily_return": r.get("last_daily_return"),
            }
        )
    holdout_wrong, train_wrong = _wrong_dir_date_sets(dump)
    flagged_set = set(flagged)
    return {
        "rule": rule.get("rule"),
        "n_flagged": len(flagged),
        "flagged_dates": sorted(flagged),
        "holdout7_wrong_overlap": sorted(flagged_set & holdout_wrong),
        "n_holdout7_wrong_overlap": len(flagged_set & holdout_wrong),
        "train_wrong_overlap_n": len(flagged_set & train_wrong),
        "dates": dates_detail,
    }


def _pick_primary_advisory_rule(results: list[dict[str, Any]]) -> dict[str, Any]:
    if not results:
        return {}
    ranked = sorted(
        results,
        key=lambda x: (
            -int(x.get("n_holdout7_wrong_overlap") or 0),
            int(x.get("n_flagged") or 0),
        ),
    )
    best = ranked[0]
    if int(best.get("n_holdout7_wrong_overlap") or 0) == 0:
        for preferred in ("advisory_ovn_pr35_lret", "advisory_ovn_pr35", "advisory_pr35_lret_bull"):
            hit = next((r for r in results if r.get("rule") == preferred), None)
            if hit and int(hit.get("n_flagged") or 0) > 0:
                return hit
    return best


def cmd_advisory_sweep(args: argparse.Namespace) -> int:
    """Sweep advisory rules on 30d (+ optional 180d overlap counts)."""
    holdout = holdout_dates_from_cf(args.counterfactual)
    per30 = enrich_per_date_doc_btc(_load(args.per_date), holdout)
    dump30 = _load(args.features) if args.features.is_file() else {}
    dump180 = _load(args.dump_180) if args.dump_180.is_file() else {}
    per180 = (
        enrich_per_date_doc_btc(_load(args.per_date_180), holdout)
        if args.per_date_180.is_file()
        else None
    )

    results_30d: list[dict[str, Any]] = []
    for rule in ADVISORY_RULES:
        row = _eval_advisory_rule(per30, rule, dump=dump30)
        if per180 is not None and dump180:
            row180 = _eval_advisory_rule(per180, rule, dump=dump180)
            row["n_flagged_180d"] = row180.get("n_flagged")
            row["train_wrong_overlap_180d"] = row180.get("train_wrong_overlap_n")
        results_30d.append(row)

    primary = _pick_primary_advisory_rule(results_30d)
    primary_rule = str(primary.get("rule") or "advisory_ovn_pr35_lret")
    manifest = {
        "schema": "btrack_advisory_bear_trap_manifest_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "research_only": True,
        "rule": primary_rule,
        "n_dates": len(primary.get("dates") or []),
        "dates": primary.get("dates") or [],
        "holdout7_wrong_overlap": primary.get("holdout7_wrong_overlap") or [],
        "operator_line": (
            f"- [MKM-ADVISORY-TRAP] rule={primary_rule} "
            f"n={len(primary.get('dates') or [])} "
            f"holdout7_wrong_hit={len(primary.get('holdout7_wrong_overlap') or [])} "
            "(direction unchanged)"
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    sweep = {
        "schema": "btrack_advisory_bear_trap_sweep_v1",
        "generated_at_utc": manifest["generated_at_utc"],
        "research_only": True,
        "primary_rule": primary_rule,
        "rules_30d": results_30d,
        "operator_lines": [
            manifest["operator_line"],
            f"- [MKM-ADVISORY-SWEEP] tested {len(ADVISORY_RULES)} rules; primary={primary_rule}",
        ],
    }
    for r in results_30d:
        sweep["operator_lines"].append(
            f"- [MKM-ADVISORY-SWEEP] {r.get('rule')}: n={r.get('n_flagged')} "
            f"h7_wrong={r.get('n_holdout7_wrong_overlap')}"
        )
    args.sweep_output.parent.mkdir(parents=True, exist_ok=True)
    args.sweep_output.write_text(json.dumps(sweep, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    print(f"WROTE: {args.sweep_output.resolve()}")
    for line in sweep["operator_lines"]:
        print(line)
    return 0


def cmd_advisory_export(args: argparse.Namespace) -> int:
    """Legacy single-rule export — delegates to advisory-sweep."""
    if not hasattr(args, "sweep_output"):
        args.sweep_output = DEFAULT_ADVISORY_SWEEP
    if not hasattr(args, "dump_180"):
        args.dump_180 = DEFAULT_DUMP_180
    if not hasattr(args, "per_date_180"):
        args.per_date_180 = DEFAULT_PER_180
    if not hasattr(args, "counterfactual"):
        args.counterfactual = DEFAULT_CF
    return cmd_advisory_sweep(args)


def cmd_full(args: argparse.Namespace) -> int:
    holdout = holdout_dates_from_cf(DEFAULT_CF)
    print("==> dump 30d", file=sys.stderr)
    _ensure_per_date(30, DEFAULT_CFG, DEFAULT_PER, force=True)
    per30 = _load(DEFAULT_PER)
    dump30 = build_feature_dump(
        per_date_doc=per30,
        score_doc=_pipeline_eval(DEFAULT_PER, 30),
        holdout_dates=holdout,
    )
    DEFAULT_DUMP.write_text(json.dumps(dump30, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("==> dump 180d", file=sys.stderr)
    _ensure_per_date(180, DEFAULT_CFG, DEFAULT_PER_180, force=True)
    per180 = _load(DEFAULT_PER_180)
    dump180 = build_feature_dump(
        per_date_doc=per180,
        score_doc=_pipeline_eval(DEFAULT_PER_180, 180),
        holdout_dates=holdout,
    )
    DEFAULT_DUMP_180.write_text(json.dumps(dump180, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(dump30["operator_line"], file=sys.stderr)
    print(dump180["operator_line"], file=sys.stderr)
    print("==> eval-grid 30d", file=sys.stderr)
    r30 = _finalize_grid_report(
        rows_out=_run_grid_sweep(dump=dump30, per_doc=per30, days=30, prod_baseline=0.366667, label="30d"),
        dump_path=DEFAULT_DUMP,
        output_path=DEFAULT_GRID,
        prod_baseline=0.366667,
        label="30d",
        n_days=30,
    )
    print("==> eval-grid 180d", file=sys.stderr)
    r180 = _finalize_grid_report(
        rows_out=_run_grid_sweep(dump=dump180, per_doc=per180, days=180, prod_baseline=0.233333, label="180d"),
        dump_path=DEFAULT_DUMP_180,
        output_path=DEFAULT_GRID_180,
        prod_baseline=0.233333,
        label="180d",
        n_days=180,
    )
    print("==> advisory sweep", file=sys.stderr)
    cmd_advisory_sweep(
        argparse.Namespace(
            features=DEFAULT_DUMP,
            per_date=DEFAULT_PER,
            dump_180=DEFAULT_DUMP_180,
            per_date_180=DEFAULT_PER_180,
            counterfactual=DEFAULT_CF,
            output=DEFAULT_ADVISORY,
            sweep_output=DEFAULT_ADVISORY_SWEEP,
        )
    )
    print("==> train_wrong pattern summary", file=sys.stderr)
    subprocess.run(
        [sys.executable, "scripts/build_btrack_train_wrong_pattern_summary_v1.py"],
        cwd=ROOT,
        check=True,
    )
    summary = {
        "schema": "btrack_wrong_dir_holdout_full_run_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dump_30d": dump30.get("operator_line"),
        "dump_180d": dump180.get("operator_line"),
        "n_train_wrong_180d": len(dump180.get("train_wrong_direction_dates") or []),
        "grid_30d_verdict": r30.get("verdict"),
        "grid_180d_verdict": r180.get("verdict"),
        "operator_lines": (r30.get("operator_lines") or []) + (r180.get("operator_lines") or []),
    }
    out = ROOT / "reports/btrack_wrong_dir_holdout_full_run_v1_latest.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out.resolve()}")
    for line in summary["operator_lines"]:
        print(line)
    return 0


def _verdict(best_h: dict | None, best_fix: dict | None, prod: float, met_key: str) -> str:
    if not best_h:
        return "no_valid_variants"
    rate = float((best_h.get(met_key) or {}).get("price_directional_hit_rate") or 0)
    h7_fix = int((best_h.get("holdout_wrong_dir") or {}).get("bear_fix") or 0)
    if rate >= 0.5 and rate >= prod and h7_fix >= 2:
        return "holdout_review_required"
    return "reject_auxiliary_promote"


def _ops_grid(
    prod: float,
    best_h: dict | None,
    best_fix: dict | None,
    best_train: dict | None,
    best_hold_neutral: dict | None,
    label: str,
    met_key: str,
) -> list[str]:
    tag = "AUX-GRID180" if label == "180d" else "AUX-GRID"
    lines = [f"- [MKM-{tag}] prod {label} baseline {prod:.1%}"]
    if best_h:
        m = best_h.get(met_key) or {}
        hw = best_h.get("holdout_wrong_dir") or {}
        lines.append(
            f"- [MKM-{tag}] best headline {best_h.get('slug')}: "
            f"{float(m.get('price_directional_hit_rate') or 0):.1%} "
            f"holdout bear_fix={hw.get('bear_fix')}/{hw.get('n_wrong_dir_days')} "
            f"A1={'pass' if best_h.get('alert_1_pass') else 'fail'}"
        )
    if best_train and best_train.get("slug") != (best_h or {}).get("slug"):
        tw = best_train.get("train_wrong_dir") or {}
        lines.append(
            f"- [MKM-{tag}] best train_wrong bear_fix {best_train.get('slug')}: "
            f"{tw.get('bear_fix')}/{tw.get('n_wrong_dir_days')}"
        )
    if best_fix and best_fix.get("slug") not in {(best_h or {}).get("slug"), (best_train or {}).get("slug")}:
        hw = best_fix.get("holdout_wrong_dir") or {}
        m = best_fix.get(met_key) or {}
        lines.append(
            f"- [MKM-{tag}] best holdout fix {best_fix.get('slug')}: bear_fix={hw.get('bear_fix')} "
            f"all-rows {float(m.get('price_directional_hit_rate') or 0):.1%}"
        )
    if best_hold_neutral:
        hn = best_hold_neutral.get("holdout_wrong_dir") or {}
        lines.append(
            f"- [MKM-{tag}] best holdout neutralize {best_hold_neutral.get('slug')}: "
            f"{hn.get('neutralized')}/{hn.get('n_wrong_dir_days')} wrong_dir days"
        )
    lines.append(f"- [MKM-{tag}] ensemble unchanged; auxiliary research_only")
    return lines


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)

    p_dump = sub.add_parser("dump", help="Build holdout feature dump JSON")
    p_dump.add_argument("--output", type=Path, default=DEFAULT_DUMP)
    p_dump.add_argument("--per-date", type=Path, default=DEFAULT_PER)
    p_dump.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    p_dump.add_argument("--counterfactual", type=Path, default=DEFAULT_CF)
    p_dump.add_argument("--ensemble-config", type=Path, default=DEFAULT_CFG)
    p_dump.add_argument("--days", type=int, default=30)
    p_dump.add_argument("--refresh-per-date", action="store_true")
    p_dump.set_defaults(func=cmd_dump)

    p_grid = sub.add_parser("eval-grid", help="Sweep auxiliary layers on 30d panel")
    p_grid.add_argument("--output", type=Path, default=DEFAULT_GRID)
    p_grid.add_argument("--features", type=Path, default=DEFAULT_DUMP)
    p_grid.add_argument("--per-date", type=Path, default=DEFAULT_PER)
    p_grid.add_argument("--days", type=int, default=30)
    p_grid.set_defaults(func=cmd_eval_grid)

    p_g180 = sub.add_parser("eval-grid-180", help="Auxiliary grid on 180d panel")
    p_g180.add_argument("--output", type=Path, default=DEFAULT_GRID_180)
    p_g180.add_argument("--features", type=Path, default=DEFAULT_DUMP_180)
    p_g180.add_argument("--per-date", type=Path, default=DEFAULT_PER_180)
    p_g180.set_defaults(func=cmd_eval_grid_180)

    p_adv = sub.add_parser("advisory-export", help="Advisory manifest (primary rule from sweep)")
    p_adv.add_argument("--output", type=Path, default=DEFAULT_ADVISORY)
    p_adv.add_argument("--sweep-output", type=Path, default=DEFAULT_ADVISORY_SWEEP)
    p_adv.add_argument("--features", type=Path, default=DEFAULT_DUMP)
    p_adv.add_argument("--dump-180", type=Path, default=DEFAULT_DUMP_180)
    p_adv.add_argument("--per-date", type=Path, default=DEFAULT_PER)
    p_adv.add_argument("--per-date-180", type=Path, default=DEFAULT_PER_180)
    p_adv.add_argument("--counterfactual", type=Path, default=DEFAULT_CF)
    p_adv.set_defaults(func=cmd_advisory_export)

    p_asw = sub.add_parser("advisory-sweep", help="Sweep advisory rules; write primary manifest")
    p_asw.add_argument("--output", type=Path, default=DEFAULT_ADVISORY)
    p_asw.add_argument("--sweep-output", type=Path, default=DEFAULT_ADVISORY_SWEEP)
    p_asw.add_argument("--features", type=Path, default=DEFAULT_DUMP)
    p_asw.add_argument("--dump-180", type=Path, default=DEFAULT_DUMP_180)
    p_asw.add_argument("--per-date", type=Path, default=DEFAULT_PER)
    p_asw.add_argument("--per-date-180", type=Path, default=DEFAULT_PER_180)
    p_asw.add_argument("--counterfactual", type=Path, default=DEFAULT_CF)
    p_asw.set_defaults(func=cmd_advisory_sweep)

    p_full = sub.add_parser("full", help="dump 30+180, both grids, advisory manifest")
    p_full.set_defaults(func=cmd_full)

    args = ap.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
