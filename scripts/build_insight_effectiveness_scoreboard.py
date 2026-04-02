# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.9, L:0.8, K:0.6, M:0.7}
# Balance: 89
# Purpose: Build daily promotion-readiness scoreboard from fused/shadow artifacts.
# Keywords: scoreboard, promotion, hit-rate, pending-close, wilson-ci
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "docs" / "final" / "artifacts"
DEFAULT_FUSED_HISTORY = ARTIFACTS / "fused_paper_cycle_decision_history.jsonl"
DEFAULT_SCORING_DISTRIBUTION = ARTIFACTS / "trinity_scoring_distribution_latest.json"
DEFAULT_SHADOW_GATE = ARTIFACTS / "independent_lens_shadow_gate_latest.json"
DEFAULT_OUT = ARTIFACTS / "insight_effectiveness_scoreboard_latest.json"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = line.strip().lstrip("\ufeff")
        if not s:
            continue
        try:
            o = json.loads(s)
        except json.JSONDecodeError:
            continue
        if isinstance(o, dict):
            rows.append(o)
    return rows


def _to_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _to_int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def _wilson_interval(successes: int, total: int, z: float = 1.96) -> tuple[float, float] | None:
    if total <= 0:
        return None
    p = successes / total
    denom = 1 + (z * z / total)
    center = (p + (z * z / (2 * total))) / denom
    half = z * math.sqrt((p * (1 - p) + (z * z / (4 * total))) / total) / denom
    return (center - half, center + half)


def _month_tag(ts_utc: str) -> str:
    return (ts_utc or "")[:7]


def _rate_from_counts(counts: dict[str, Any]) -> float:
    hit = _to_int(counts.get("HIT"))
    fail = _to_int(counts.get("FAIL"))
    neutral = _to_int(counts.get("NEUTRAL_DRAW"))
    denom = hit + fail + neutral
    if denom <= 0:
        return 0.0
    return hit / denom


def main() -> int:
    ap = argparse.ArgumentParser(description="Build Insight Effectiveness Scoreboard.")
    ap.add_argument("--fused-history", type=Path, default=DEFAULT_FUSED_HISTORY)
    ap.add_argument("--scoring-distribution", type=Path, default=DEFAULT_SCORING_DISTRIBUTION)
    ap.add_argument("--shadow-gate", type=Path, default=DEFAULT_SHADOW_GATE)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--pending-close-threshold", type=float, default=0.30)
    ap.add_argument("--hit-rate-threshold", type=float, default=0.55)
    ap.add_argument("--state-present-rate-threshold", type=float, default=0.20)
    args = ap.parse_args()

    history_rows = _read_jsonl(args.fused_history)
    scoring = _read_json(args.scoring_distribution)
    shadow_gate = _read_json(args.shadow_gate)

    latest = history_rows[-1] if history_rows else {}
    counts = latest.get("counts") if isinstance(latest.get("counts"), dict) else {}
    rates = latest.get("rates") if isinstance(latest.get("rates"), dict) else {}

    hit = _to_int(counts.get("HIT"))
    fail = _to_int(counts.get("FAIL"))
    neutral = _to_int(counts.get("NEUTRAL_DRAW"))
    pending = _to_int(counts.get("PENDING_CLOSE"))
    resolved_plus_neutral_n = hit + fail + neutral
    hit_rate_resolved_plus_neutral = (
        hit / resolved_plus_neutral_n if resolved_plus_neutral_n > 0 else 0.0
    )
    ci = _wilson_interval(hit, resolved_plus_neutral_n)

    # Keep latest record per month, preserving chronological order.
    monthly_latest: dict[str, dict[str, Any]] = {}
    monthly_order: list[str] = []
    for row in history_rows:
        ts_utc = str(row.get("generated_at_utc") or "")
        key = _month_tag(ts_utc)
        if not key:
            continue
        if key not in monthly_latest:
            monthly_order.append(key)
        monthly_latest[key] = row

    last_two_months = monthly_order[-2:]
    monthly_rates: list[dict[str, Any]] = []
    for m in last_two_months:
        row = monthly_latest[m]
        c = row.get("counts") if isinstance(row.get("counts"), dict) else {}
        monthly_rates.append(
            {
                "month_tag": m,
                "hit_rate_resolved_plus_neutral": _rate_from_counts(c),
                "sample_size": _to_int(row.get("sample_size")),
            }
        )

    pending_close_rate = _to_float(rates.get("pending_close_rate_raw"))
    state_all = (
        (scoring.get("dual_regime_state") or {}).get("all")
        if isinstance(scoring.get("dual_regime_state"), dict)
        else {}
    )
    advisory = (
        (scoring.get("dual_regime_state") or {}).get("advisory")
        if isinstance(scoring.get("dual_regime_state"), dict)
        else {}
    )
    state_present_rate = _to_float((state_all or {}).get("state_id_present_rate"))
    state_not_wired = str((advisory or {}).get("decision") or "") == "state_signal_not_wired"

    cond_pending_ok = pending_close_rate <= args.pending_close_threshold
    cond_hit_two_months_ok = len(monthly_rates) >= 2 and all(
        mr["hit_rate_resolved_plus_neutral"] >= args.hit_rate_threshold for mr in monthly_rates
    )
    cond_state_ok = (state_present_rate >= args.state_present_rate_threshold) and (not state_not_wired)

    is_ready = cond_pending_ok and cond_hit_two_months_ok and cond_state_ok
    readiness = "PROMOTION_APPROVED_6W_PILOT" if is_ready else "KEEP_OBSERVATION_ONLY"

    payload: dict[str, Any] = {
        "schema": "insight_effectiveness_scoreboard_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sources": {
            "fused_history_path": str(args.fused_history.resolve()),
            "scoring_distribution_path": str(args.scoring_distribution.resolve()),
            "shadow_gate_path": str(args.shadow_gate.resolve()),
        },
        "thresholds": {
            "pending_close_rate_max": args.pending_close_threshold,
            "monthly_hit_rate_min": args.hit_rate_threshold,
            "state_present_rate_min": args.state_present_rate_threshold,
            "required_consecutive_months": 2,
        },
        "latest_window_snapshot": {
            "counts": {
                "HIT": hit,
                "FAIL": fail,
                "NEUTRAL_DRAW": neutral,
                "PENDING_CLOSE": pending,
            },
            "pending_close_rate_raw": pending_close_rate,
            "hit_rate_resolved_plus_neutral": hit_rate_resolved_plus_neutral,
            "resolved_plus_neutral_n": resolved_plus_neutral_n,
            "hit_rate_resolved_plus_neutral_wilson95": {
                "lower": ci[0] if ci else None,
                "upper": ci[1] if ci else None,
            },
        },
        "monthly_hit_rate_trace": monthly_rates,
        "state_signal_snapshot": {
            "state_present_rate_all": state_present_rate,
            "advisory_decision": (advisory or {}).get("decision"),
        },
        "shadow_gate_snapshot": {
            "decision": shadow_gate.get("decision"),
            "weekly_cycles_observed": ((shadow_gate.get("history") or {}).get("weekly_cycles_observed")),
            "monthly_cycles_observed": ((shadow_gate.get("history") or {}).get("monthly_cycles_observed")),
        },
        "checks": {
            "pending_close_rate_ok": cond_pending_ok,
            "monthly_hit_rate_two_months_ok": cond_hit_two_months_ok,
            "state_signal_wired_ok": cond_state_ok,
        },
        "is_promotion_ready": is_ready,
        "promotion_status": readiness,
        "note": "Daily machine verdict for B-track to A-track promotion readiness.",
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out.resolve()}")
    print(f"is_promotion_ready={is_ready} status={readiness}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
