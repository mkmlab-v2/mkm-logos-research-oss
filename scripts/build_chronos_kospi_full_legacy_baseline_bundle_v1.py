#!/usr/bin/env python3
"""[HYPO] Consolidate Chronos-Forward legacy baseline artifacts vs daily WF research arms."""
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

DEFAULT_TRAINING = ROOT / "data/chronos_forward_training/training_result.json"
DEFAULT_HOLDOUT = ROOT / "data/chronos_forward_training/holdout_2026_result.json"
DEFAULT_WF = ROOT / "reports/kospi_prophecy_wf_holdout_compare_v1_latest.json"
DEFAULT_CHRONOS2 = ROOT / "reports/rq025_chronos2_kospi_daily_wf_shadow_v1_latest.json"
DEFAULT_TIMESFM = ROOT / "reports/rq025_timesfm25_kospi_daily_wf_shadow_v1_latest.json"
DEFAULT_DUAL = ROOT / "reports/kospi_prophecy_operational_dual_lane_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/chronos_kospi_full_legacy_baseline_bundle_v1_latest.json"
DEFAULT_FULL_SNAPS = ROOT / "data/chronos_forward_training/training_snapshots_full.json"
SCHEMA = "chronos_kospi_full_legacy_baseline_bundle_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _rate(obj: dict[str, Any] | None, key: str = "direction_match_rate") -> float | None:
    if not obj:
        return None
    val = obj.get(key)
    if val is None:
        return None
    try:
        r = float(val)
    except (TypeError, ValueError):
        return None
    return round(r / 100.0, 6) if r > 1.0 else round(r, 6)


def _holdout_window(snapshots: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not snapshots:
        return None
    dates = [f"{s.get('year')}-{int(s.get('month')):02d}" for s in snapshots if s.get("year") and s.get("month")]
    if not dates:
        return None
    return {"start": dates[0], "end": dates[-1], "n_snapshots": len(snapshots)}


def _blind_holdout_2026(full_snapshots_path: Path) -> dict[str, Any] | None:
    payload = _load(full_snapshots_path)
    if not payload:
        return None
    rows = payload.get("snapshots") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        return None
    blind = [s for s in rows if s.get("year") == 2026 and s.get("direction_match") is not None]
    if not blind:
        return None
    hits = sum(1 for s in blind if s.get("direction_match"))
    return {
        "n": len(blind),
        "direction_match_count": hits,
        "directional_hit_rate": round(hits / len(blind), 6),
        "months": [f"{s.get('year')}-{int(s.get('month')):02d}" for s in blind if s.get("month")],
        "caveat": (
            f"2026 blind months from training_snapshots_full (end_month={blind[-1].get('month') if blind else '?'}); "
            "monthly legacy stack; not comparable to daily WF"
        ),
        "end_month_inferred": max(int(s.get("month") or 0) for s in blind) if blind else None,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--training-json", type=Path, default=DEFAULT_TRAINING)
    ap.add_argument("--holdout-json", type=Path, default=DEFAULT_HOLDOUT)
    ap.add_argument("--wf-json", type=Path, default=DEFAULT_WF)
    ap.add_argument("--chronos2-json", type=Path, default=DEFAULT_CHRONOS2)
    ap.add_argument("--timesfm-json", type=Path, default=DEFAULT_TIMESFM)
    ap.add_argument("--dual-lane-json", type=Path, default=DEFAULT_DUAL)
    ap.add_argument("--full-snapshots-json", type=Path, default=DEFAULT_FULL_SNAPS)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    training = _load(args.training_json)
    holdout = _load(args.holdout_json)
    wf = _load(args.wf_json)
    chronos2 = _load(args.chronos2_json)
    timesfm = _load(args.timesfm_json)
    dual = _load(args.dual_lane_json)

    training_rate = _rate(training)
    holdout_rate = _rate(holdout)
    holdout_snaps = holdout.get("snapshots") if holdout else None
    holdout_window = _holdout_window(holdout_snaps if isinstance(holdout_snaps, list) else [])

    wf_arms = ((wf or {}).get("blocked_walkforward_test_only") or {}).get("arms") or []
    wf_by_id = {a.get("arm_id"): a for a in wf_arms if isinstance(a, dict)}

    c2_summary = (chronos2 or {}).get("chronos2_zero_shot_summary") or {}
    c2_pooled = c2_summary.get("pooled_test_directional_hit_rate")
    if c2_pooled is None:
        for arm in ((chronos2 or {}).get("blocked_walkforward_test_only") or {}).get("arms") or []:
            if arm.get("arm_id") == "chronos2_zero_shot":
                c2_pooled = arm.get("pooled_test_directional_hit_rate")
                break

    tfm_pooled = ((timesfm or {}).get("timesfm25_zero_shot_summary") or {}).get(
        "pooled_test_directional_hit_rate"
    )
    if tfm_pooled is None:
        for arm in ((timesfm or {}).get("blocked_walkforward_test_only") or {}).get("arms") or []:
            if arm.get("arm_id") == "timesfm25_zero_shot":
                tfm_pooled = arm.get("pooled_test_directional_hit_rate")
                break

    lanes = (dual or {}).get("lanes") or {}
    frozen_30d = (lanes.get("frozen_bear_panel") or {}).get("price_directional_hit_rate")
    per_date_30d = (lanes.get("per_date_kospi_causal") or {}).get("price_directional_hit_rate")

    full_training_done = bool(training and int(training.get("total_iterations") or 0) >= 360)
    full_holdout_walk_done = bool(holdout and int(holdout.get("total_iterations") or 0) >= 360)
    holdout_is_scoped_poc = bool(
        holdout_window
        and holdout_window.get("n_snapshots", 0) < 100
        and holdout_window.get("start", "") >= "2025"
        and not full_holdout_walk_done
    )
    blind_2026 = _blind_holdout_2026(args.full_snapshots_json)
    blind_end_month = (blind_2026 or {}).get("end_month_inferred")

    out: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "track_a_mutated": False,
        "legacy_chronos_forward": {
            "training_full_362_pointer": str(args.training_json.relative_to(ROOT)).replace("\\", "/"),
            "training_full_362_on_disk": full_training_done,
            "training_direction_match_rate": training_rate,
            "training_total_iterations": (training or {}).get("total_iterations"),
            "training_timestamp": (training or {}).get("timestamp"),
            "holdout_pointer": str(args.holdout_json.relative_to(ROOT)).replace("\\", "/"),
            "holdout_direction_match_rate": holdout_rate,
            "holdout_window": holdout_window,
            "holdout_is_scoped_poc_not_full_walk": holdout_is_scoped_poc,
            "holdout_full_walk_362_on_disk": full_holdout_walk_done,
            "holdout_blind_2026_only": blind_2026,
            "holdout_timestamp": (holdout or {}).get("timestamp"),
            "runner": "scripts/run_chronos_forward_kospi_baseline.ps1",
        },
        "daily_research_arms_pointer": {
            "wf_holdout_compare": str(args.wf_json.relative_to(ROOT)).replace("\\", "/"),
            "chronos2_wf_shadow": str(args.chronos2_json.relative_to(ROOT)).replace("\\", "/"),
            "timesfm25_wf_shadow": str(args.timesfm_json.relative_to(ROOT)).replace("\\", "/"),
            "operational_dual_lane_30d": str(args.dual_lane_json.relative_to(ROOT)).replace("\\", "/"),
        },
        "rates_table": [
            {
                "arm_id": "legacy_training_full_walk_monthly",
                "granularity": "monthly",
                "protocol": f"ChronosForwardTrainer 1996-01..2026-{blind_end_month or 2:02d} walk-forward (in-sample cumulative)",
                "directional_hit_rate": training_rate,
                "n": (training or {}).get("successful_predictions"),
                "caveat": "not OOS holdout; monthly not daily",
            },
            {
                "arm_id": "legacy_holdout2026_artifact",
                "granularity": "monthly",
                "protocol": "holdout_2026_result.json on disk (scoped PoC if n<100 & start>=2025)",
                "directional_hit_rate": holdout_rate,
                "n": (holdout or {}).get("successful_predictions"),
                "caveat": "see holdout_is_scoped_poc_not_full_walk",
            },
            {
                "arm_id": "wf_majority_from_train",
                "granularity": "daily",
                "protocol": "252d blocked WF OOS pooled",
                "directional_hit_rate": (wf_by_id.get("majority_from_train") or {}).get("pooled_test_directional_hit_rate"),
                "n": (wf_by_id.get("majority_from_train") or {}).get("total_n_evaluated"),
            },
            {
                "arm_id": "wf_per_date_kospi_ensemble",
                "granularity": "daily",
                "protocol": "252d blocked WF OOS pooled",
                "directional_hit_rate": (wf_by_id.get("per_date_kospi_ensemble") or {}).get("pooled_test_directional_hit_rate"),
                "n": (wf_by_id.get("per_date_kospi_ensemble") or {}).get("total_n_evaluated"),
            },
            {
                "arm_id": "chronos2_zero_shot_daily",
                "granularity": "daily",
                "protocol": "252d blocked WF OOS pooled",
                "directional_hit_rate": c2_pooled,
                "n": None,
            },
            {
                "arm_id": "timesfm25_zero_shot_daily",
                "granularity": "daily",
                "protocol": "252d blocked WF OOS pooled",
                "directional_hit_rate": tfm_pooled,
                "n": None,
            },
            {
                "arm_id": "kospi_operational_frozen_30d",
                "granularity": "daily",
                "protocol": "in-sample frozen panel",
                "directional_hit_rate": frozen_30d,
                "n": 30,
            },
            {
                "arm_id": "kospi_operational_per_date_30d",
                "granularity": "daily",
                "protocol": "in-sample per-date causal",
                "directional_hit_rate": per_date_30d,
                "n": 30,
            },
        ],
        "interpretation_ko": [
            f"training_result.json 362iter={'있음' if full_training_done else '없음'} — direction_match_rate={training_rate} (월별 in-sample walk).",
            f"holdout_2026 full walk 362={'완료' if full_holdout_walk_done else '미완'} — aggregate rate={holdout_rate}.",
            f"2026 blind-only (model update skipped): {blind_2026}" if blind_2026 else "2026 blind-only: n/a",
            "일별 OOS SSOT는 wf_holdout_compare (majority 63.2% pooled) — legacy monthly와 단위·프로토콜 상이.",
            "chronos2 daily OOS 52.7% — legacy holdout PoC(41.2%)보다 높으나 WF majority 미달.",
            f"timesfm25 daily OOS pooled={tfm_pooled} — chronos2 대비 +{round((tfm_pooled or 0) - (c2_pooled or 0), 4) if tfm_pooled and c2_pooled else 'n/a'}pp; WF majority 미달.",
            "Track A·headline·live 자동 교체 없음.",
        ],
        "next_manual": [
            "combined_all_passed human sign-off 전 Track A·headline·live 변경 금지",
        ],
        "reproduce": (
            "py scripts/run_chronos_forward_kospi_baseline.py --mode holdout2026 "
            "--end-month 6 --no-use-gpu --no-holdout-pattern-correction && "
            "py scripts/build_chronos_kospi_full_legacy_baseline_bundle_v1.py"
        ),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"WROTE: {args.output.resolve()} training_362={full_training_done} "
        f"holdout_362={full_holdout_walk_done} training_rate={training_rate} "
        f"holdout_rate={holdout_rate} blind_2026={ (blind_2026 or {}).get('directional_hit_rate') }"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
