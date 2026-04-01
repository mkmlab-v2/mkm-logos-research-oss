#!/usr/bin/env python3
"""Build rolling 5/10-day Trinity scoring distribution report from waiting queue log."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _read_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = line.strip().lstrip("\ufeff")
        if not s:
            continue
        try:
            obj = json.loads(s)
        except Exception:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _window_stats(decisions: list[str]) -> dict[str, Any]:
    total = len(decisions)
    hit = sum(1 for x in decisions if x == "HIT")
    fail = sum(1 for x in decisions if x == "FAIL")
    neutral = sum(1 for x in decisions if x == "NEUTRAL_DRAW")
    pending = sum(1 for x in decisions if x == "PENDING_CLOSE")
    def _rate(v: int) -> float | None:
        return round(v / total, 4) if total > 0 else None

    advisory = "insufficient_data"
    if total >= 3:
        if fail >= 2:
            advisory = "risk_high_reduce_size_or_tighten_entry"
        elif neutral / total >= 0.6:
            advisory = "signal_weak_review_thresholds"
        elif hit / total >= 0.6:
            advisory = "signal_stable_keep_thresholds"
        else:
            advisory = "mixed_keep_observe"
    return {
        "sample_size": total,
        "hit": hit,
        "fail": fail,
        "neutral_draw": neutral,
        "pending_close": pending,
        "hit_rate": _rate(hit),
        "fail_rate": _rate(fail),
        "neutral_draw_rate": _rate(neutral),
        "pending_close_rate": _rate(pending),
        "advisory": advisory,
    }


def _window_dual_regime_stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    if total == 0:
        return {
            "sample_size": 0,
            "state_id_present_count": 0,
            "state_id_present_rate": None,
            "clamp_count": 0,
            "clamp_rate": None,
            "source_counts": {},
            "top_source": None,
        }

    present_count = 0
    clamp_count = 0
    source_counts: dict[str, int] = {}
    for row in rows:
        src = str(row.get("dual_regime_state_source") or "none")
        source_counts[src] = source_counts.get(src, 0) + 1
        if bool(row.get("dual_regime_state_present", False)):
            present_count += 1
        clamp_val = row.get("dual_regime_state_clamp_count")
        if isinstance(clamp_val, (int, float)):
            clamp_count += int(clamp_val > 0)
        elif row.get("dual_regime_state_clamp_ratio") is not None:
            try:
                clamp_count += int(float(row.get("dual_regime_state_clamp_ratio")) > 0.0)
            except Exception:
                pass

    top_source = max(source_counts.items(), key=lambda kv: kv[1])[0] if source_counts else None
    return {
        "sample_size": total,
        "state_id_present_count": present_count,
        "state_id_present_rate": round(present_count / total, 4),
        "clamp_count": clamp_count,
        "clamp_rate": round(clamp_count / total, 4),
        "source_counts": dict(sorted(source_counts.items(), key=lambda kv: kv[1], reverse=True)),
        "top_source": top_source,
    }


def _dual_regime_advisory(stats: dict[str, Any]) -> dict[str, Any]:
    """Produce threshold-based advisory from dual_regime_state all-window stats."""
    sample_size = int(stats.get("sample_size") or 0)
    top_source = str(stats.get("top_source") or "none")
    clamp_rate = stats.get("clamp_rate")
    present_rate = stats.get("state_id_present_rate")

    decision = "insufficient_data"
    reason = "sample_lt_3"
    if sample_size >= 3:
        clamp_rate_v = float(clamp_rate) if clamp_rate is not None else 0.0
        present_rate_v = float(present_rate) if present_rate is not None else 0.0
        if top_source == "none" and present_rate_v < 0.2:
            decision = "state_signal_not_wired"
            reason = "top_source_none_and_present_rate_low"
        elif clamp_rate_v >= 0.6:
            decision = "state_clamp_high_tight_mode"
            reason = "clamp_rate_ge_0.6"
        elif clamp_rate_v >= 0.3:
            decision = "state_clamp_active_review_thresholds"
            reason = "clamp_rate_ge_0.3"
        else:
            decision = "state_clamp_stable"
            reason = "clamp_rate_lt_0.3"
    return {
        "decision": decision,
        "reason": reason,
        "thresholds": {
            "present_rate_low": 0.2,
            "clamp_rate_warn": 0.3,
            "clamp_rate_high": 0.6,
        },
    }


def _auto_hold_override_stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    override_rows = [r for r in rows if r.get("auto_hold_promotion") is True]
    total = len(override_rows)
    if total == 0:
        return {
            "count": 0,
            "trigger_counts": {},
            "priority_counts": {},
            "top_trigger": None,
        }

    trigger_counts: dict[str, int] = {}
    priority_counts: dict[str, int] = {}
    for row in override_rows:
        trigger = str(row.get("override_trigger_type") or "unknown")
        trigger_counts[trigger] = trigger_counts.get(trigger, 0) + 1
        priority = row.get("override_priority")
        key = str(int(priority)) if isinstance(priority, (int, float)) else "unknown"
        priority_counts[key] = priority_counts.get(key, 0) + 1
    trigger_counts = dict(sorted(trigger_counts.items(), key=lambda kv: kv[1], reverse=True))
    priority_counts = dict(sorted(priority_counts.items(), key=lambda kv: kv[1], reverse=True))
    return {
        "count": total,
        "trigger_counts": trigger_counts,
        "priority_counts": priority_counts,
        "top_trigger": next(iter(trigger_counts.keys()), None),
    }


def _auto_hold_override_advisory(stats: dict[str, Any]) -> dict[str, Any]:
    count = int(stats.get("count") or 0)
    top_trigger = str(stats.get("top_trigger") or "")
    trigger_counts = stats.get("trigger_counts") if isinstance(stats.get("trigger_counts"), dict) else {}
    top_count = int(trigger_counts.get(top_trigger, 0)) if top_trigger else 0

    decision = "insufficient_data"
    reason = "count_lt_3"
    top_ratio = None
    if count > 0 and top_count > 0:
        top_ratio = round(top_count / count, 4)
    if count >= 3:
        ratio = float(top_ratio or 0.0)
        if top_trigger == "net_source_fallback" and ratio >= 0.7:
            decision = "override_skew_net_source_fallback"
            reason = "top_trigger_net_source_fallback_ratio_ge_0.7"
        elif top_trigger == "dual_regime_state_clamp" and ratio >= 0.7:
            decision = "override_skew_dual_regime_state_clamp"
            reason = "top_trigger_dual_regime_state_clamp_ratio_ge_0.7"
        else:
            decision = "override_mix_balanced"
            reason = "no_single_trigger_ratio_ge_0.7"
    return {
        "decision": decision,
        "reason": reason,
        "top_trigger_ratio": top_ratio,
        "thresholds": {
            "minimum_count": 3,
            "skew_ratio": 0.7,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Report rolling Trinity scoring distribution.")
    ap.add_argument(
        "--log-path",
        default="docs/final/artifacts/waiting_queue_monthly_check_log.jsonl",
    )
    ap.add_argument(
        "--output",
        default="docs/final/artifacts/trinity_scoring_distribution_latest.json",
    )
    ap.add_argument("--metric", default="BTC_BINANCE_D1_RETURN_PCT")
    args = ap.parse_args()

    log_path = Path(args.log_path)
    out_path = Path(args.output)
    rows = _read_rows(log_path)
    metric = str(args.metric)

    filtered = [r for r in rows if str(r.get("hypothesis_metric") or "") == metric]
    decisions = [str(r.get("post_close_eval_decision") or "") for r in filtered]
    decisions = [d for d in decisions if d in {"HIT", "FAIL", "NEUTRAL_DRAW", "PENDING_CLOSE"}]

    stats_5 = _window_stats(decisions[-5:])
    stats_10 = _window_stats(decisions[-10:])
    dual_5 = _window_dual_regime_stats(filtered[-5:])
    dual_10 = _window_dual_regime_stats(filtered[-10:])
    dual_all = _window_dual_regime_stats(filtered)
    dual_advisory = _dual_regime_advisory(dual_all)
    override_5 = _auto_hold_override_stats(filtered[-5:])
    override_10 = _auto_hold_override_stats(filtered[-10:])
    override_all = _auto_hold_override_stats(filtered)
    override_advisory = _auto_hold_override_advisory(override_all)

    report = {
        "schema": "trinity_scoring_distribution_v1",
        "generated_at_utc": _utc_now(),
        "log_path": str(log_path),
        "metric": metric,
        "windows": {
            "d5": stats_5,
            "d10": stats_10,
        },
        "dual_regime_state": {
            "d5": dual_5,
            "d10": dual_10,
            "all": dual_all,
            "advisory": dual_advisory,
        },
        "auto_hold_overrides": {
            "d5": override_5,
            "d10": override_10,
            "all": override_all,
            "advisory": override_advisory,
        },
        "latest_decision": decisions[-1] if decisions else None,
        "total_filtered_rows": len(filtered),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
