#!/usr/bin/env python3
"""[HYPO] KOSPI per-date Phase B ablation: overnight overlay on/off × v1/v2 (clean panel)."""
from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.btrack_ensemble_per_date_core_v1 import compute_per_date_direction_rows  # noqa: E402
from scripts.build_btrack_prophecy_score_from_ohlcv import (  # noqa: E402
    _actual_direction,
    _last_n_intersection_trading_dates,
    _row_pair_for_eval_date,
)
from scripts.logos_shadow_eval_lib import load_kospi_yf_rows  # noqa: E402

DEFAULT_BUNDLE = ROOT / "docs/final/artifacts/btrack_llm_input_bundle_latest.json"
DEFAULT_CFG = ROOT / "docs/final/artifacts/btrack_lens_ensemble_v1.json"
DEFAULT_BTC = ROOT / "research/market_data/btc_daily_external_yf.csv"
DEFAULT_KOSPI = ROOT / "research/market_data/kospi_daily_external_yf.csv"
DEFAULT_FLOW = ROOT / "research/market_data/kospi_monthly_flow_external.csv"
DEFAULT_OUT = ROOT / "reports/kospi_per_date_phase_b_ablation_v1_latest.json"
PROBE_DATE = "2026-05-29"

VARIANTS: list[dict[str, Any]] = [
    {"slug": "v1_overnight_on", "ensemble_mode": "v1", "kospi_overnight_overlay_enabled": True},
    {"slug": "v1_overnight_off", "ensemble_mode": "v1", "kospi_overnight_overlay_enabled": False},
    {"slug": "v2_overnight_on", "ensemble_mode": "v2_confidence_fusion", "kospi_overnight_overlay_enabled": True},
    {"slug": "v2_overnight_off", "ensemble_mode": "v2_confidence_fusion", "kospi_overnight_overlay_enabled": False},
    {
        "slug": "v1_overnight_off_margin035",
        "ensemble_mode": "v1",
        "kospi_overnight_overlay_enabled": False,
        "tie_break_min_margin": 0.035,
    },
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _eval_dates(kospi_csv: Path, btc_csv: Path, n: int) -> list[str]:
    kospi_rows = load_kospi_yf_rows(kospi_csv)
    btc_rows = load_kospi_yf_rows(btc_csv)
    return _last_n_intersection_trading_dates(kospi_rows, btc_rows, n)


def _bad_dates(kospi_rows: list[dict[str, Any]], dates: list[str], *, max_abs: float) -> set[str]:
    out: set[str] = set()
    for ed in dates:
        pair = _row_pair_for_eval_date(kospi_rows, ed)
        if pair is None:
            continue
        prev_r, cur_r = pair
        ret = abs((float(cur_r["close"]) - float(prev_r["close"])) / float(prev_r["close"]))
        if ret > max_abs:
            out.add(ed)
    return out


def _metrics(
    rows: list[dict[str, Any]],
    kospi_rows: list[dict[str, Any]],
    *,
    neutral_bps: float,
    exclude: set[str],
) -> dict[str, Any]:
    hits = n = 0
    dist: Counter[str] = Counter()
    for r in rows:
        ed = str(r.get("eval_date") or "")[:10]
        if not ed or ed in exclude:
            continue
        pred = str(r.get("predicted_direction") or "neutral")
        pair = _row_pair_for_eval_date(kospi_rows, ed)
        if pair is None:
            continue
        prev_r, cur_r = pair
        ret = (float(cur_r["close"]) - float(prev_r["close"])) / float(prev_r["close"])
        act = _actual_direction(ret, neutral_bps)
        n += 1
        dist[pred] += 1
        if pred == act:
            hits += 1
    return {
        "hits": hits,
        "n": n,
        "hit_rate": round(hits / n, 4) if n else None,
        "pred_distribution": dict(dist),
    }


def _flow_row_for_month(flow_csv: Path, ym: str) -> dict[str, Any] | None:
    if not flow_csv.is_file():
        return None
    import csv

    with flow_csv.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if str(row.get("ym") or row.get("month") or "").strip() == ym:
                return row
    return None


def _run_rows(spec: dict[str, Any], *, eval_dates: list[str], base_cfg: dict[str, Any], bundle: dict[str, Any]) -> list[dict[str, Any]]:
    cfg = copy.deepcopy(base_cfg)
    rules = dict(cfg.get("rules") or {})
    rules["price_instrument"] = "kospi"
    rules["enforce_btc_only_guard"] = False
    if "ensemble_mode" in spec:
        rules["ensemble_mode"] = spec["ensemble_mode"]
    if "kospi_overnight_overlay_enabled" in spec:
        rules["kospi_overnight_overlay_enabled"] = bool(spec["kospi_overnight_overlay_enabled"])
    for k in ("tie_break_min_margin", "min_direction_confidence", "neutral_penalty"):
        if k in spec:
            rules[k] = spec[k]
    cfg["rules"] = rules
    return compute_per_date_direction_rows(
        bundle=bundle,
        ensemble_cfg=cfg,
        eval_dates=eval_dates,
        ohlc_csv=DEFAULT_KOSPI,
        instrument="kospi",
    )


def _apply_best_dual(
    *,
    best_spec: dict[str, Any],
    eval_dates: list[str],
    base_cfg: dict[str, Any],
    bundle: dict[str, Any],
) -> int:
    """Write kospi tmp + merge via dual builder with --ensemble-config override."""
    work = ROOT / "reports" / "_phase_b_ablation_work"
    work.mkdir(parents=True, exist_ok=True)
    cfg_path = work / "kospi_ensemble_best.json"
    cfg = copy.deepcopy(base_cfg)
    rules = dict(cfg.get("rules") or {})
    rules["price_instrument"] = "kospi"
    rules["enforce_btc_only_guard"] = False
    if "ensemble_mode" in best_spec:
        rules["ensemble_mode"] = best_spec["ensemble_mode"]
    if "kospi_overnight_overlay_enabled" in best_spec:
        rules["kospi_overnight_overlay_enabled"] = bool(best_spec["kospi_overnight_overlay_enabled"])
    for k in ("tie_break_min_margin", "min_direction_confidence"):
        if k in best_spec:
            rules[k] = best_spec[k]
    cfg["rules"] = rules
    cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    kospi_tmp = work / "kospi_rows.json"
    ens_cmd = [
        sys.executable,
        str(ROOT / "scripts/build_btrack_ensemble_per_date_directions_v1.py"),
        "--recent-trading-days",
        str(len(eval_dates)),
        "--target-instrument",
        "kospi",
        "--ensemble-config",
        str(cfg_path.relative_to(ROOT)),
        "--output",
        str(kospi_tmp.relative_to(ROOT)),
    ]
    rc = subprocess.run(ens_cmd, cwd=str(ROOT)).returncode
    if rc != 0:
        return rc
    btc_cmd = [
        sys.executable,
        str(ROOT / "scripts/build_btrack_ensemble_per_date_directions_v1.py"),
        "--recent-trading-days",
        str(len(eval_dates)),
        "--target-instrument",
        "btc",
        "--output",
        str((work / "btc_rows.json").relative_to(ROOT)),
    ]
    rc = subprocess.run(btc_cmd, cwd=str(ROOT)).returncode
    if rc != 0:
        return rc
    from scripts.build_btrack_dual_per_date_directions_v1 import merge_dual_documents

    merge_dual_documents(
        kospi_doc=_load(kospi_tmp),
        btc_doc=_load(work / "btc_rows.json"),
        dual_out=ROOT / "reports/btrack_ensemble_per_date_directions_dual_v1_latest.json",
        btc_legacy_out=ROOT / "reports/btrack_ensemble_per_date_directions_v1_latest.json",
    )
    score_cmd = [
        sys.executable,
        str(ROOT / "scripts/build_btrack_prophecy_score_from_ohlcv.py"),
        "--recent-trading-days",
        str(len(eval_dates)),
        "--force-dual-leg-panel",
        "--btc-csv",
        str(DEFAULT_BTC),
        "--per-date-direction-json",
        "reports/btrack_ensemble_per_date_directions_dual_v1_latest.json",
        "--output",
        "docs/final/artifacts/btrack_prophecy_score_latest.json",
    ]
    return subprocess.run(score_cmd, cwd=str(ROOT)).returncode


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--recent-trading-days", type=int, default=30)
    ap.add_argument("--neutral-bps", type=float, default=5.0)
    ap.add_argument("--max-abs-daily-return", type=float, default=0.15)
    ap.add_argument("--apply-best", action="store_true", help="Promote best variant to dual+score artifacts")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    bundle = _load(DEFAULT_BUNDLE)
    base_cfg = _load(DEFAULT_CFG)
    eval_dates = _eval_dates(DEFAULT_KOSPI, DEFAULT_BTC, max(1, int(args.recent_trading_days)))
    kospi_rows = load_kospi_yf_rows(DEFAULT_KOSPI)
    exclude = _bad_dates(kospi_rows, eval_dates, max_abs=float(args.max_abs_daily_return))

    results: list[dict[str, Any]] = []
    probe: dict[str, Any] = {}
    for spec in VARIANTS:
        rows = _run_rows(spec, eval_dates=eval_dates, base_cfg=base_cfg, bundle=bundle)
        m = _metrics(rows, kospi_rows, neutral_bps=float(args.neutral_bps), exclude=exclude)
        row_probe = next((r for r in rows if str(r.get("eval_date") or "")[:10] == PROBE_DATE), None)
        if row_probe:
            probe[spec["slug"]] = {
                "predicted_direction": row_probe.get("predicted_direction"),
                "preliminary_direction": row_probe.get("preliminary_direction"),
                "weighted_score": row_probe.get("weighted_score"),
                "confidence": row_probe.get("confidence"),
                "lens_values": row_probe.get("lens_values"),
                "kospi_overnight_overlay": (row_probe.get("lens_values") or {}),
            }
        results.append({"slug": spec["slug"], "overrides": {k: v for k, v in spec.items() if k != "slug"}, **m})

    best = max((r for r in results if r.get("hit_rate") is not None), key=lambda x: x["hit_rate"], default=None)
    best_spec = next((s for s in VARIANTS if s["slug"] == best.get("slug")), None) if best else None

    flow_may = _flow_row_for_month(DEFAULT_FLOW, "2026-05")
    pair_0529 = _row_pair_for_eval_date(kospi_rows, PROBE_DATE)
    ret_0529 = None
    if pair_0529:
        prev_r, cur_r = pair_0529
        ret_0529 = round((float(cur_r["close"]) - float(prev_r["close"])) / float(prev_r["close"]) * 100, 3)

    out: dict[str, Any] = {
        "schema": "kospi_per_date_phase_b_ablation_v1",
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "generated_at_utc": _utc_now(),
        "eval_dates_n": len(eval_dates),
        "excluded_bad_ohlcv_dates": sorted(exclude),
        "neutral_bps": float(args.neutral_bps),
        "variants": results,
        "best_by_clean_kospi_hit_rate": best,
        "probe_date": PROBE_DATE,
        "probe_2026_05_29": {
            "kospi_ret_pct": ret_0529,
            "actual_direction": _actual_direction((ret_0529 or 0) / 100.0, float(args.neutral_bps)) if ret_0529 is not None else None,
            "monthly_flow_2026_05": flow_may,
            "per_variant": probe,
            "note_ko": "bear 예측·bull 실현; BTC leg은 bear 적중. 수급·오버나이트·macro/news 정적 bundle 영향 후보.",
        },
        "note": "Clean panel KOSPI leg only; not WF holdout. overnight via rules.kospi_overnight_overlay_enabled.",
    }

    apply_rc = None
    if args.apply_best and best_spec:
        apply_rc = _apply_best_dual(
            best_spec=best_spec,
            eval_dates=eval_dates,
            base_cfg=base_cfg,
            bundle=bundle,
        )
        out["apply_best"] = {"slug": best_spec["slug"], "exit_code": apply_rc}

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()} best={best.get('slug') if best else None} hr={best.get('hit_rate') if best else None}")
    if apply_rc is not None:
        print(f"apply_best exit={apply_rc}")
    return 0 if apply_rc in (None, 0) else int(apply_rc)


if __name__ == "__main__":
    raise SystemExit(main())
