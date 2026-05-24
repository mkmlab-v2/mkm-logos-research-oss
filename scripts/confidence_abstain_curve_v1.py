#!/usr/bin/env python3
"""Confidence abstain curve — pre-registered B-track filters vs call rate / skill.

research_only [HYPO] — does not mutate prophecy_hit_rate_eval_latest.json or live trading.

Reads fixed presets from docs/final/artifacts/confidence_abstain_policy_v1.1.json (or --policy-json),
joins ensemble per-date features with score-json actuals, emits call_rate vs skill table.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "docs/final/artifacts/confidence_abstain_policy_v1.1.json"
DEFAULT_SCORE = ROOT / "docs/final/artifacts/btrack_prophecy_score_latest.json"
DEFAULT_BUNDLE = ROOT / "docs/final/artifacts/btrack_llm_input_bundle_latest.json"
DEFAULT_CFG = ROOT / "docs/final/artifacts/btrack_lens_ensemble_v1.json"
DEFAULT_BTC = ROOT / "research/market_data/btc_daily_external_yf.csv"
DEFAULT_KOSPI = ROOT / "research/market_data/kospi_daily_external_yf.csv"
DEFAULT_OUT = ROOT / "reports/confidence_abstain_curve_v1_latest.json"
SCHEMA = "confidence_abstain_curve_v1"
MIN_PANEL_ROWS = 20


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _sign_from_score(score: float, *, epsilon: float) -> str | None:
    if score > epsilon:
        return "bull"
    if score < -epsilon:
        return "bear"
    return None


def lens_unanimous_direction(
    lens_values: dict[str, Any] | None,
    *,
    lens_keys: list[str],
    min_lenses: int,
    epsilon: float,
) -> tuple[bool, str | None]:
    """All signaled lenses share one direction; count must be >= min_lenses."""
    if not isinstance(lens_values, dict):
        return False, None
    signs: list[str] = []
    for key in lens_keys:
        block = lens_values.get(key)
        if not isinstance(block, dict):
            continue
        s = _sign_from_score(_safe_float(block.get("score")), epsilon=epsilon)
        if s:
            signs.append(s)
    if len(signs) < min_lenses:
        return False, None
    if len(set(signs)) != 1:
        return False, None
    return True, signs[0]


def lens_majority_agreement_direction(
    lens_values: dict[str, Any] | None,
    *,
    lens_keys: list[str],
    min_lenses_agree: int,
    epsilon: float,
) -> tuple[bool, str | None]:
    """At least min_lenses_agree lenses share the majority bull/bear sign."""
    if not isinstance(lens_values, dict):
        return False, None
    signs: list[str] = []
    for key in lens_keys:
        block = lens_values.get(key)
        if not isinstance(block, dict):
            continue
        s = _sign_from_score(_safe_float(block.get("score")), epsilon=epsilon)
        if s:
            signs.append(s)
    if len(signs) < min_lenses_agree:
        return False, None
    bull = sum(1 for s in signs if s == "bull")
    bear = sum(1 for s in signs if s == "bear")
    if bull >= min_lenses_agree and bull > bear:
        return True, "bull"
    if bear >= min_lenses_agree and bear > bull:
        return True, "bear"
    return False, None


def signal_direction_from_row(row: dict[str, Any], *, use_preliminary: bool) -> str:
    if use_preliminary:
        pre = str(row.get("preliminary_direction") or "").strip().lower()
        if pre in ("bull", "bear"):
            return pre
    pred = str(row.get("predicted_direction") or "").strip().lower()
    if pred in ("bull", "bear"):
        return pred
    ws = _safe_float(row.get("weighted_score"))
    sign = _sign_from_score(ws, epsilon=1e-9)
    return sign if sign else "neutral"


def apply_abstain_preset_to_direction(
    row: dict[str, Any],
    preset: dict[str, Any],
    *,
    lens_keys: list[str],
    min_lenses: int,
    lens_epsilon: float,
) -> tuple[str, dict[str, Any]]:
    use_prelim = bool(preset.get("use_preliminary_direction", True))
    signal = signal_direction_from_row(row, use_preliminary=use_prelim)
    conf = max(0.0, min(1.0, _safe_float(row.get("confidence"))))
    margin = abs(_safe_float(row.get("weighted_score")))
    meta: dict[str, Any] = {
        "signal_direction": signal,
        "confidence": round(conf, 6),
        "abs_weighted_margin": round(margin, 6),
    }

    if signal not in ("bull", "bear"):
        meta["abstain_reason"] = "non_directional_signal"
        return "neutral", meta

    min_conf = _safe_float(preset.get("min_confidence"))
    if conf < min_conf:
        meta["abstain_reason"] = "below_min_confidence"
        return "neutral", meta

    min_margin = _safe_float(preset.get("min_abs_weighted_margin"))
    if margin < min_margin:
        meta["abstain_reason"] = "below_min_abs_weighted_margin"
        return "neutral", meta

    lens_min_agree = preset.get("lens_min_agree")
    need_lens = preset.get("require_lens_unanimous") or lens_min_agree is not None
    if need_lens:
        lv = row.get("lens_values") if isinstance(row.get("lens_values"), dict) else None
        if lens_min_agree is not None:
            min_lens_req = max(1, int(lens_min_agree))
            ok, agreed = lens_majority_agreement_direction(
                lv,
                lens_keys=lens_keys,
                min_lenses_agree=min_lens_req,
                epsilon=lens_epsilon,
            )
        else:
            min_lens_req = min_lenses
            ok, agreed = lens_unanimous_direction(
                lv,
                lens_keys=lens_keys,
                min_lenses=min_lens_req,
                epsilon=lens_epsilon,
            )
        meta["lens_agreement_ok"] = ok
        meta["lens_agreement_direction"] = agreed
        meta["lens_min_agree_required"] = min_lens_req
        if not ok:
            meta["abstain_reason"] = "lens_agreement_insufficient"
            return "neutral", meta
        if agreed and agreed != signal:
            meta["abstain_reason"] = "lens_signal_mismatch"
            return "neutral", meta

    meta["abstain_reason"] = None
    return signal, meta


def metric_bundle(rows: list[dict[str, Any]]) -> dict[str, Any]:
    hits_all = 0
    n_all = 0
    hits_dir = 0
    n_calls = 0
    n_abstain = 0
    for r in rows:
        pd = str(r.get("predicted_direction") or "").strip().lower()
        ad = str(r.get("actual_direction") or "").strip().lower()
        if not pd or not ad or pd not in ("bull", "bear", "neutral") or ad not in ("bull", "bear", "neutral"):
            continue
        n_all += 1
        if pd == ad:
            hits_all += 1
        if pd == "neutral":
            n_abstain += 1
            continue
        n_calls += 1
        if pd == ad:
            hits_dir += 1
    call_rate = (n_calls / n_all) if n_all else None
    headline_skill = (hits_all / n_all) if n_all else None
    directional_skill = (hits_dir / n_calls) if n_calls else None
    return {
        "n_evaluated": n_all,
        "n_directional_calls": n_calls,
        "n_abstain": n_abstain,
        "call_rate": round(call_rate, 6) if call_rate is not None else None,
        "headline_skill": round(headline_skill, 6) if headline_skill is not None else None,
        "directional_skill": round(directional_skill, 6) if directional_skill is not None else None,
        "directional_call_hits": hits_dir,
        "headline_hits": hits_all,
    }


def eval_dates_from_recent_trading_days(
    *,
    kospi_csv: Path,
    btc_csv: Path,
    n: int,
) -> list[str]:
    if n < 1:
        return []
    _ensure_root_on_path()
    from scripts.build_btrack_prophecy_score_from_ohlcv import _last_n_intersection_trading_dates
    from scripts.logos_shadow_eval_lib import load_kospi_yf_rows

    kospi_rows = load_kospi_yf_rows(kospi_csv)
    btc_rows = load_kospi_yf_rows(btc_csv)
    return _last_n_intersection_trading_dates(kospi_rows, btc_rows, n)


def _ensure_root_on_path() -> None:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))


def btc_actual_direction_by_date(
    btc_csv: Path,
    eval_dates: list[str],
    *,
    neutral_bps: float = 5.0,
) -> dict[str, str]:
    _ensure_root_on_path()
    from scripts.build_btrack_prophecy_score_from_ohlcv import (
        _actual_direction,
        _daily_return,
        _row_pair_for_eval_date,
    )
    from scripts.logos_shadow_eval_lib import load_kospi_yf_rows

    rows = load_kospi_yf_rows(btc_csv)
    ohlc = [{"date": str(r["date"])[:10], "close": float(r["close"])} for r in rows]
    out: dict[str, str] = {}
    for ed in eval_dates:
        pair = _row_pair_for_eval_date(ohlc, ed)
        if pair is None:
            continue
        ret = _daily_return(pair[0], pair[1])
        out[ed] = _actual_direction(ret, neutral_bps)
    return out


def join_ensemble_with_actuals(
    ensemble_rows: list[dict[str, Any]],
    actual_by_date: dict[str, str],
    *,
    instrument: str,
) -> list[dict[str, Any]]:
    inst = instrument.strip().lower()
    joined: list[dict[str, Any]] = []
    for row in ensemble_rows:
        if str(row.get("instrument") or "btc").strip().lower() != inst:
            continue
        ed = str(row.get("eval_date") or "")[:10]
        ad = actual_by_date.get(ed)
        if not ed or not ad:
            continue
        merged = dict(row)
        merged["actual_direction"] = ad
        joined.append(merged)
    return sorted(joined, key=lambda x: str(x.get("eval_date") or ""))


def join_score_actuals(
    ensemble_rows: list[dict[str, Any]],
    score_rows: list[dict[str, Any]],
    *,
    instrument: str,
) -> list[dict[str, Any]]:
    inst = instrument.strip().lower()
    actual_by_date: dict[str, str] = {}
    for r in score_rows:
        if str(r.get("instrument") or "").strip().lower() != inst:
            continue
        ed = str(r.get("eval_date") or "")[:10]
        if ed:
            actual_by_date[ed] = str(r.get("actual_direction") or "").strip().lower()
    return join_ensemble_with_actuals(ensemble_rows, actual_by_date, instrument=inst)


def score_panel_rows(score_doc: dict[str, Any], *, instrument: str) -> list[dict[str, Any]]:
    inst = instrument.strip().lower()
    raw = score_doc.get("rows") if isinstance(score_doc.get("rows"), list) else []
    out: list[dict[str, Any]] = []
    for r in raw:
        if not isinstance(r, dict):
            continue
        if str(r.get("instrument") or "").strip().lower() != inst:
            continue
        ed = str(r.get("eval_date") or "")[:10]
        pd = str(r.get("predicted_direction") or "").strip().lower()
        ad = str(r.get("actual_direction") or "").strip().lower()
        if not ed or not pd or not ad:
            continue
        out.append(
            {
                "eval_date": ed,
                "instrument": inst,
                "predicted_direction": pd,
                "actual_direction": ad,
                "confidence": r.get("confidence"),
                "source": "score_json",
            }
        )
    return sorted(out, key=lambda x: x["eval_date"])


def eval_dates_from_score(score_doc: dict[str, Any], *, instrument: str) -> list[str]:
    return [r["eval_date"] for r in score_panel_rows(score_doc, instrument=instrument)]


def split_train_holdout(
    rows: list[dict[str, Any]], holdout_n: int
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if holdout_n <= 0 or holdout_n >= len(rows):
        return rows, []
    return rows[:-holdout_n], rows[-holdout_n:]


def evaluate_preset(
    *,
    preset: dict[str, Any],
    joined_ensemble: list[dict[str, Any]],
    score_panel: list[dict[str, Any]],
    holdout_n: int,
    lens_keys: list[str],
    min_lenses: int,
    lens_epsilon: float,
) -> dict[str, Any]:
    source = str(preset.get("source") or "ensemble_per_date").strip().lower()
    if source == "score_json":
        panel_rows = score_panel
    else:
        panel_rows = []
        for row in joined_ensemble:
            if preset.get("apply_min_direction_confidence_from_config"):
                pred = str(row.get("predicted_direction") or "neutral").strip().lower()
            else:
                pred, _ = apply_abstain_preset_to_direction(
                    row,
                    preset,
                    lens_keys=lens_keys,
                    min_lenses=min_lenses,
                    lens_epsilon=lens_epsilon,
                )
            panel_rows.append(
                {
                    "eval_date": row["eval_date"],
                    "instrument": row.get("instrument"),
                    "predicted_direction": pred,
                    "actual_direction": row["actual_direction"],
                }
            )

    train_rows, holdout_rows = split_train_holdout(panel_rows, holdout_n)
    full_metrics = metric_bundle(panel_rows)
    train_metrics = metric_bundle(train_rows)
    holdout_metrics = metric_bundle(holdout_rows) if holdout_rows else None

    return {
        "policy_id": preset.get("policy_id"),
        "label_ko": preset.get("label_ko"),
        "description": preset.get("description"),
        "source": source,
        "full_panel": full_metrics,
        "train_split": train_metrics,
        "holdout_split": holdout_metrics,
        "holdout_n_days": len(holdout_rows),
        "train_n_days": len(train_rows),
    }


def build_ensemble_joined(
    *,
    bundle_path: Path,
    cfg_path: Path,
    btc_csv: Path,
    eval_dates: list[str],
) -> list[dict[str, Any]]:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts.btrack_ensemble_per_date_core_v1 import compute_per_date_direction_rows

    bundle = _load_json(bundle_path)
    cfg = _load_json(cfg_path) if cfg_path.is_file() else {}
    rows = compute_per_date_direction_rows(
        bundle=bundle,
        ensemble_cfg=cfg,
        eval_dates=eval_dates,
        btc_csv=btc_csv,
        instrument="btc",
    )
    return rows


def build_abstain_curve_document(
    *,
    policy: dict[str, Any],
    eval_dates: list[str],
    joined: list[dict[str, Any]],
    score_panel: list[dict[str, Any]],
    inputs_meta: dict[str, Any],
    holdout_n: int,
) -> dict[str, Any]:
    lens_cfg = policy.get("lens_unanimous") if isinstance(policy.get("lens_unanimous"), dict) else {}
    lens_keys = [str(k) for k in (lens_cfg.get("lens_keys") or ["price", "macro", "news"])]
    min_lenses = int(lens_cfg.get("min_lenses_with_signal") or 3)
    lens_epsilon = _safe_float(lens_cfg.get("score_epsilon"), 1e-6)

    eval_set = set(eval_dates)
    b0_panel = [r for r in score_panel if r.get("eval_date") in eval_set]

    presets = policy.get("presets") if isinstance(policy.get("presets"), list) else []
    curve_rows: list[dict[str, Any]] = []
    for preset in presets:
        if not isinstance(preset, dict):
            continue
        score_for_preset = b0_panel if str(preset.get("source") or "").strip().lower() == "score_json" else score_panel
        curve_rows.append(
            evaluate_preset(
                preset=preset,
                joined_ensemble=joined,
                score_panel=score_for_preset,
                holdout_n=holdout_n,
                lens_keys=lens_keys,
                min_lenses=min_lenses,
                lens_epsilon=lens_epsilon,
            )
        )

    b0_partial = len(b0_panel) < len(joined)
    return {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "track_wall": policy.get("track_wall"),
        "policy_version": policy.get("version"),
        "policy_frozen_at_utc": policy.get("frozen_at_utc"),
        "inputs": {
            **inputs_meta,
            "n_eval_dates": len(eval_dates),
            "n_joined_rows": len(joined),
            "eval_date_first": eval_dates[0] if eval_dates else None,
            "eval_date_last": eval_dates[-1] if eval_dates else None,
            "b0_score_rows_in_window": len(b0_panel),
            "b0_operational_score_partial_window": b0_partial,
            "b0_partial_note": (
                "B0 uses operational score-json overlap only; P0/P1/P1.5/P2 use full calendar window."
                if b0_partial
                else None
            ),
        },
        "holdout": {"last_n_trading_days": holdout_n},
        "presets": curve_rows,
        "operator_lines": _operator_lines(curve_rows),
        "guardrails": [
            "Presets are pre-registered in confidence_abstain_policy_v1.1.json (no post-hoc threshold tuning).",
            "Does not write prophecy_hit_rate_eval_latest.json or enable live trading.",
            "directional_skill rises when call_rate falls — report both columns together.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--policy-json", type=Path, default=DEFAULT_POLICY)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--bundle-json", type=Path, default=DEFAULT_BUNDLE)
    ap.add_argument("--ensemble-config", type=Path, default=DEFAULT_CFG)
    ap.add_argument("--btc-csv", type=Path, default=DEFAULT_BTC)
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI)
    ap.add_argument("--instrument", default="btc")
    ap.add_argument("--neutral-bps", type=float, default=5.0)
    ap.add_argument(
        "--recent-trading-days",
        type=int,
        default=0,
        help="When >0, panel dates from KOSPI∩BTC calendar (actuals from BTC OHLCV).",
    )
    ap.add_argument("--output", type=Path, default=None)
    ap.add_argument(
        "--min-panel-rows",
        type=int,
        default=0,
        help="Exit 2 if panel smaller than this (0 = use MIN_PANEL_ROWS or recent-trading-days).",
    )
    args = ap.parse_args(argv)

    recent_n = max(0, int(args.recent_trading_days))
    min_rows = int(args.min_panel_rows)
    if min_rows <= 0:
        min_rows = max(MIN_PANEL_ROWS, recent_n) if recent_n > 0 else MIN_PANEL_ROWS

    out_path = args.output
    if out_path is None:
        out_path = (
            ROOT / f"reports/confidence_abstain_curve_v1_{recent_n}d_latest.json"
            if recent_n > 0
            else DEFAULT_OUT
        )

    for p in (args.policy_json, args.bundle_json, args.btc_csv):
        if not p.is_file():
            print(f"Missing: {p}", file=sys.stderr)
            return 2
    if recent_n > 0 and not args.kospi_csv.is_file():
        print(f"Missing kospi csv for --recent-trading-days: {args.kospi_csv}", file=sys.stderr)
        return 2
    if not args.score_json.is_file():
        print(f"Missing score-json (B0 overlap): {args.score_json}", file=sys.stderr)
        return 2

    policy = _load_json(args.policy_json)
    score_doc = _load_json(args.score_json)
    score_panel = score_panel_rows(score_doc, instrument=args.instrument)

    if recent_n > 0:
        eval_dates = eval_dates_from_recent_trading_days(
            kospi_csv=args.kospi_csv, btc_csv=args.btc_csv, n=recent_n
        )
        actual_by_date = btc_actual_direction_by_date(
            args.btc_csv, eval_dates, neutral_bps=float(args.neutral_bps)
        )
    else:
        eval_dates = eval_dates_from_score(score_doc, instrument=args.instrument)
        actual_by_date = btc_actual_direction_by_date(
            args.btc_csv, eval_dates, neutral_bps=float(args.neutral_bps)
        )

    if not eval_dates:
        print("No eval_dates resolved for panel.", file=sys.stderr)
        return 2

    ensemble_rows = build_ensemble_joined(
        bundle_path=args.bundle_json,
        cfg_path=args.ensemble_config,
        btc_csv=args.btc_csv,
        eval_dates=eval_dates,
    )
    joined = join_ensemble_with_actuals(
        ensemble_rows, actual_by_date, instrument=args.instrument
    )
    if len(joined) < min_rows:
        print(
            f"Panel too short: joined={len(joined)} required>={min_rows}.",
            file=sys.stderr,
        )
        return 2

    holdout_cfg = policy.get("holdout") if isinstance(policy.get("holdout"), dict) else {}
    holdout_n = int(holdout_cfg.get("last_n_trading_days") or 10)

    inputs_meta = {
        "policy_json": str(args.policy_json.relative_to(ROOT)).replace("\\", "/"),
        "score_json": str(args.score_json.relative_to(ROOT)).replace("\\", "/"),
        "bundle_json": str(args.bundle_json.relative_to(ROOT)).replace("\\", "/"),
        "ensemble_config": str(args.ensemble_config.relative_to(ROOT)).replace("\\", "/"),
        "instrument": args.instrument,
        "recent_trading_days": recent_n if recent_n > 0 else None,
        "neutral_bps": float(args.neutral_bps),
        "actuals_source": "btc_ohlcv" if recent_n > 0 else "btc_ohlcv_with_score_fallback_dates",
    }

    out_doc = build_abstain_curve_document(
        policy=policy,
        eval_dates=eval_dates,
        joined=joined,
        score_panel=score_panel,
        inputs_meta=inputs_meta,
        holdout_n=holdout_n,
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path.resolve()} presets={len(out_doc['presets'])} panel={len(joined)}")
    for line in out_doc["operator_lines"]:
        print(line)
    return 0


def _operator_lines(curve_rows: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for row in curve_rows:
        pid = row.get("policy_id")
        m = row.get("full_panel") if isinstance(row.get("full_panel"), dict) else {}
        cr = m.get("call_rate")
        ds = m.get("directional_skill")
        hs = m.get("headline_skill")
        nc = m.get("n_directional_calls")
        ne = m.get("n_evaluated")
        h = row.get("holdout_split") if isinstance(row.get("holdout_split"), dict) else {}
        hds = h.get("directional_skill")
        hnc = h.get("n_directional_calls")
        lines.append(
            f"- [ABSTAIN-CURVE] {pid}: call_rate={cr} directional_skill={ds} "
            f"headline={hs} calls={nc}/{ne} holdout_dir={hds} (n={hnc})"
        )
    return lines


if __name__ == "__main__":
    raise SystemExit(main())
