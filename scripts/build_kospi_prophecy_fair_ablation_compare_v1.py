#!/usr/bin/env python3
"""[HYPO] Fair KOSPI frozen vs per-date ablation compare — unified neutral_bps + straw-man baselines."""
from __future__ import annotations

import argparse
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

DEFAULT_OUT = ROOT / "reports/kospi_prophecy_fair_ablation_compare_v1_latest.json"
DEFAULT_WF = ROOT / "reports/rq025_chronos2_kospi_daily_wf_shadow_v1_latest.json"
DEFAULT_DUAL_LANE = ROOT / "reports/kospi_prophecy_operational_dual_lane_v1_latest.json"
WORK_FROZEN = ROOT / "reports/_kospi_fair_ablation_frozen_tmp.json"
WORK_CAUSAL = ROOT / "reports/_kospi_fair_ablation_causal_tmp.json"
DEFAULT_DUAL = ROOT / "reports/btrack_ensemble_per_date_directions_dual_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _kospi_rows(doc: dict[str, Any], *, exclude: set[str]) -> list[dict[str, Any]]:
    return [
        r
        for r in (doc.get("rows") or [])
        if isinstance(r, dict)
        and str(r.get("instrument") or "").lower() == "kospi"
        and str(r.get("eval_date") or "")[:10] not in exclude
    ]


def _metrics_for_preds(rows: list[dict[str, Any]], preds: dict[str, str]) -> dict[str, Any]:
    hits = n = 0
    dist: Counter[str] = Counter()
    for r in rows:
        ed = str(r.get("eval_date") or "")[:10]
        pred = preds.get(ed, str(r.get("predicted_direction") or ""))
        act = str(r.get("actual_direction") or "")
        if not ed or not act:
            continue
        n += 1
        dist[pred] += 1
        if pred == act:
            hits += 1
    return {
        "hits": hits,
        "n": n,
        "hit_rate": round(hits / n, 6) if n else None,
        "pred_distribution": dict(dist),
    }


def _eval_score(path: Path, *, instrument: str = "kospi") -> dict[str, Any]:
    out = ROOT / "reports/_kospi_fair_ablation_eval_tmp.json"
    rc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/eval_prophecy_hit_rate_v1.py"),
            "--run-mode",
            "price",
            "--score-json",
            str(path),
            "--headline-instrument",
            instrument,
            "--output",
            str(out),
        ],
        cwd=str(ROOT),
    ).returncode
    if rc != 0 or not out.is_file():
        return {"price_directional_hit_rate": None, "n_evaluated": 0, "price_hits": 0}
    doc = _load(out) or {}
    m = doc.get("metrics") or {}
    return {
        "price_directional_hit_rate": m.get("price_directional_hit_rate"),
        "n_evaluated": m.get("n_evaluated") or 0,
        "price_hits": m.get("price_hits") or 0,
    }


def _pred_distribution(rows: list[dict[str, Any]]) -> dict[str, int]:
    c: Counter[str] = Counter()
    for r in rows:
        c[str(r.get("predicted_direction") or "")] += 1
    return dict(c)


def _straw_man_baselines(rows: list[dict[str, Any]]) -> dict[str, Any]:
    acts = [str(r.get("actual_direction") or "") for r in rows if r.get("actual_direction")]
    act_dist = Counter(acts)
    majority = act_dist.most_common(1)[0][0] if act_dist else "neutral"
    dates = [str(r.get("eval_date") or "")[:10] for r in rows]
    baselines: dict[str, dict[str, Any]] = {}
    for arm_id, direction in (
        ("always_majority_class", majority),
        ("always_bull", "bull"),
        ("always_bear", "bear"),
        ("always_neutral", "neutral"),
    ):
        preds = {d: direction for d in dates}
        baselines[arm_id] = {
            "fixed_prediction": direction,
            **_metrics_for_preds(rows, preds),
        }
    baselines["_actual_distribution"] = dict(act_dist)
    baselines["_majority_class"] = majority
    return baselines


def _build_scores(
    *,
    recent_days: int,
    neutral_bps: float,
    dual_json: Path,
) -> int:
    hyp = ROOT / "docs/final/artifacts/btrack_hypothesis_prophecy_latest.json"
    btc = ROOT / "research/market_data/btc_daily_external_yf.csv"
    base_cmd = [
        sys.executable,
        str(ROOT / "scripts/build_btrack_prophecy_score_from_ohlcv.py"),
        "--hypothesis-json",
        str(hyp),
        "--btc-csv",
        str(btc),
        "--force-dual-leg-panel",
        "--recent-trading-days",
        str(recent_days),
        "--neutral-bps",
        str(neutral_bps),
    ]
    if not dual_json.is_file():
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/build_btrack_dual_per_date_directions_v1.py"),
                "--recent-trading-days",
                str(recent_days),
            ],
            cwd=str(ROOT),
            check=False,
        )
    rc = subprocess.run([*base_cmd, "--output", str(WORK_FROZEN)], cwd=str(ROOT)).returncode
    if rc != 0:
        return rc
    return subprocess.run(
        [
            *base_cmd,
            "--per-date-direction-json",
            str(dual_json),
            "--output",
            str(WORK_CAUSAL),
        ],
        cwd=str(ROOT),
    ).returncode


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--recent-trading-days", type=int, default=30)
    ap.add_argument("--neutral-bps", type=float, default=5.0, help="Unified bps for frozen + per-date")
    ap.add_argument("--dual-json", type=Path, default=DEFAULT_DUAL)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    rc = _build_scores(
        recent_days=int(args.recent_trading_days),
        neutral_bps=float(args.neutral_bps),
        dual_json=args.dual_json,
    )
    if rc != 0:
        return rc

    frozen_doc = _load(WORK_FROZEN) or {}
    causal_doc = _load(WORK_CAUSAL) or {}
    bad: set[str] = set()
    for r in _kospi_rows(causal_doc, exclude=set()):
        try:
            if abs(float(r.get("daily_return") or 0.0)) > 0.15:
                bad.add(str(r.get("eval_date") or "")[:10])
        except (TypeError, ValueError):
            continue
    bad = {d for d in bad if d}

    frozen_rows = _kospi_rows(frozen_doc, exclude=bad)
    causal_rows = _kospi_rows(causal_doc, exclude=bad)
    frozen_m = _eval_score(WORK_FROZEN)
    causal_m = _eval_score(WORK_CAUSAL)
    frozen_m["pred_distribution"] = _pred_distribution(frozen_rows)
    frozen_m["mode"] = "frozen_single_direction_from_today_hypothesis"
    causal_m["pred_distribution"] = _pred_distribution(causal_rows)
    causal_m["mode"] = "per_date_direction_json_kospi_ensemble"
    straw = _straw_man_baselines(causal_rows)

    delta_pp = None
    f_hr = frozen_m.get("price_directional_hit_rate")
    c_hr = causal_m.get("price_directional_hit_rate")
    if f_hr is not None and c_hr is not None:
        delta_pp = round((c_hr - f_hr) * 100, 2)

    wf_doc = _load(DEFAULT_WF) or {}
    mom20 = None
    for arm in ((wf_doc.get("blocked_walkforward_test_only") or {}).get("arms") or []):
        if arm.get("arm_id") == "mom_20d":
            mom20 = arm.get("mean_test_directional_hit_rate")
            break

    legacy = _load(DEFAULT_DUAL_LANE) or {}
    legacy_delta = legacy.get("delta_per_date_minus_frozen_pp")

    out: dict[str, Any] = {
        "schema": "kospi_prophecy_fair_ablation_compare_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "track_a_mutated": False,
        "window": {
            "recent_trading_days": int(args.recent_trading_days),
            "neutral_bps_unified": float(args.neutral_bps),
            "n_evaluated": causal_m.get("n"),
            "excluded_bad_ohlcv_dates": sorted(bad),
        },
        "primary_compare_same_bps": {
            "frozen_operational_panel": frozen_m,
            "per_date_causal_kospi": causal_m,
            "delta_per_date_minus_frozen_pp": delta_pp,
            "hits_gained": (causal_m.get("price_hits") or 0) - (frozen_m.get("price_hits") or 0),
        },
        "straw_man_baselines_same_panel": {
            k: v for k, v in straw.items() if not k.startswith("_")
        },
        "straw_man_meta": {
            "actual_distribution": straw.get("_actual_distribution"),
            "majority_class": straw.get("_majority_class"),
        },
        "external_reference_baselines": {
            "legacy_dual_lane_mixed_bps_delta_pp": legacy_delta,
            "legacy_note": "frozen 8bps vs per-date 5bps — see kospi_prophecy_operational_dual_lane_v1_latest.json",
            "wf_mom_20d_mean_test_directional_hr": mom20,
            "wf_note": "252d blocked walk-forward OOS test blocks — not same 30d panel",
        },
        "interpretation_ko": [
            f"동일 neutral_bps={args.neutral_bps}에서 frozen vs per-date delta={delta_pp}pp.",
            "always_majority는 이 패널에서 '장세만 따라가기' 상한선; per-date가 이를 넘으면 적응 가치, 못 넘으면 ablation만으로 α 단정 금지.",
            "WF mom_20d와 majority baseline은 프로토콜·창이 다름 — 직접 우열 단정 금지.",
            "Track A·headline·live 자동 교체 없음; combined_all_passed(daily_shadow) 별도.",
        ],
        "reproduce": (
            f"py scripts/build_kospi_prophecy_fair_ablation_compare_v1.py "
            f"--recent-trading-days {args.recent_trading_days} --neutral-bps {args.neutral_bps}"
        ),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    maj_hr = (straw.get("always_majority_class") or {}).get("hit_rate")
    print(
        f"WROTE: {args.output.resolve()} unified_bps={args.neutral_bps} "
        f"frozen={frozen_m.get('price_directional_hit_rate')} per_date={causal_m.get('price_directional_hit_rate')} "
        f"delta_pp={delta_pp} majority={maj_hr}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
