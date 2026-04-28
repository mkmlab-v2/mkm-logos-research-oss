#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "docs" / "final" / "artifacts"
REPORTS = ROOT / "reports"

DEFAULT_CANARY_LOG = REPORTS / "l1_inverse_decoder_mode_router_v3_canary_log_v1.jsonl"
DEFAULT_LONGSAMPLE_GATE = ART / "l1_inverse_decoder_swap_typo_mode_router_decoder_v3_longsample_gate_v1.json"
DEFAULT_OUT = ART / "l1_inverse_decoder_mode_router_v3_codebook_expansion_recommendation_latest.json"


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _parse_ts(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw:
            continue
        try:
            rows.append(json.loads(raw))
        except json.JSONDecodeError:
            continue
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--canary-log", type=Path, default=DEFAULT_CANARY_LOG)
    ap.add_argument("--longsample-gate", type=Path, default=DEFAULT_LONGSAMPLE_GATE)
    ap.add_argument("--lookback-days", type=int, default=7)
    ap.add_argument("--min-samples", type=int, default=5)
    ap.add_argument("--latency-warning-delta-ms", type=float, default=-5.0)
    ap.add_argument("--uplift-warning-delta", type=float, default=0.003)
    ap.add_argument(
        "--domain-signal-json",
        type=Path,
        default=None,
        help="Optional domain-level failure/coverage signal JSON. If omitted, domain-target recommendation is skipped.",
    )
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    now = _now_utc()
    cutoff = now - timedelta(days=max(1, args.lookback_days))

    canary_log = args.canary_log if args.canary_log.is_absolute() else ROOT / args.canary_log
    longsample_gate = args.longsample_gate if args.longsample_gate.is_absolute() else ROOT / args.longsample_gate
    out = args.out if args.out.is_absolute() else ROOT / args.out
    domain_signal = args.domain_signal_json if args.domain_signal_json is None or args.domain_signal_json.is_absolute() else ROOT / args.domain_signal_json

    rows = _read_jsonl(canary_log)
    recent: list[dict[str, Any]] = []
    for row in rows:
        ts = row.get("ts_utc")
        if not isinstance(ts, str):
            continue
        try:
            if _parse_ts(ts) >= cutoff:
                recent.append(row)
        except ValueError:
            continue

    recent_sorted = sorted(recent, key=lambda r: r.get("ts_utc", ""))
    sample_count = len(recent_sorted)
    keep_count = sum(1 for r in recent_sorted if r.get("action") == "KEEP_CANARY")
    rollback_count = sum(1 for r in recent_sorted if r.get("action") == "ROLLBACK_TO_V4")
    keep_rate = float(keep_count) / float(max(1, sample_count))

    latency_deltas = [float(r.get("swap_typo_p95_latency_delta_ms", 0.0)) for r in recent_sorted]
    exact_deltas = [float(r.get("swap_typo_delta_exact", 0.0)) for r in recent_sorted]
    recovery_deltas = [float(r.get("swap_typo_delta_recovery", 0.0)) for r in recent_sorted]

    avg_latency_delta = sum(latency_deltas) / float(max(1, len(latency_deltas)))
    avg_exact_delta = sum(exact_deltas) / float(max(1, len(exact_deltas)))
    avg_recovery_delta = sum(recovery_deltas) / float(max(1, len(recovery_deltas)))

    gate_doc = _read_json(longsample_gate)
    gate_decision = gate_doc.get("gate", {}).get("decision")
    gate_all_ok = bool(gate_doc.get("gate", {}).get("all_ok", False))
    hard_ok = bool(gate_doc.get("gate", {}).get("hard_all_ok", gate_all_ok))

    domain_signal_present = bool(domain_signal and domain_signal.exists())
    domain_signal_summary: dict[str, Any] | None = None
    if domain_signal_present and domain_signal is not None:
        try:
            ds = _read_json(domain_signal)
            domain_signal_summary = {
                "path": str(domain_signal),
                "schema": ds.get("schema"),
                "note": "Loaded domain signal JSON (custom interpretation required per schema).",
            }
        except Exception:
            domain_signal_summary = {
                "path": str(domain_signal),
                "error": "failed_to_parse_domain_signal_json",
            }

    recommendation = "HOLD_STABILIZE_AND_OBSERVE"
    why: list[str] = []
    if sample_count < args.min_samples:
        recommendation = "HOLD_NEED_MORE_OBSERVATION"
        why.append("insufficient_recent_samples")
    elif not hard_ok:
        recommendation = "HOLD_HARD_GATE_UNSTABLE"
        why.append("hard_gate_not_ok")
    elif rollback_count > 0:
        recommendation = "HOLD_RELIABILITY_VOLATILE"
        why.append("recent_rollbacks_present")
    elif avg_latency_delta > args.latency_warning_delta_ms:
        recommendation = "HOLD_LATENCY_MARGIN_THIN"
        why.append("latency_margin_not_comfortable")
    elif avg_exact_delta < args.uplift_warning_delta or avg_recovery_delta < args.uplift_warning_delta:
        recommendation = "HOLD_QUALITY_MARGIN_THIN"
        why.append("quality_uplift_margin_not_comfortable")
    else:
        recommendation = "NO_EXPANSION_NEEDED_YET"
        why.append("canary_stable_with_quality_and_latency_headroom")

    if recommendation == "NO_EXPANSION_NEEDED_YET" and not domain_signal_present:
        why.append("domain_targeting_skipped_no_domain_signal")

    out_doc = {
        "schema": "l1_mode_router_v3_codebook_expansion_recommendation_v1",
        "generated_at_utc": now.replace(microsecond=0).isoformat(),
        "research_only": True,
        "inputs": {
            "canary_log": str(canary_log),
            "longsample_gate": str(longsample_gate),
            "lookback_days": args.lookback_days,
            "min_samples": args.min_samples,
            "latency_warning_delta_ms": args.latency_warning_delta_ms,
            "uplift_warning_delta": args.uplift_warning_delta,
            "domain_signal_json": str(domain_signal) if domain_signal is not None else None,
        },
        "window_stats": {
            "sample_count": sample_count,
            "keep_count": keep_count,
            "rollback_count": rollback_count,
            "keep_rate": keep_rate,
            "avg_swap_typo_exact_delta": avg_exact_delta,
            "avg_swap_typo_recovery_delta": avg_recovery_delta,
            "avg_swap_typo_p95_latency_delta_ms": avg_latency_delta,
        },
        "gate_snapshot": {
            "decision": gate_decision,
            "all_ok": gate_all_ok,
            "hard_all_ok": hard_ok,
        },
        "domain_signal": domain_signal_summary,
        "recommendation": recommendation,
        "why": why,
        "next_actions": [
            "continue_7day_burnin_monitoring",
            "trigger_domain_codebook_expansion_only_if_recommendation_starts_with_HOLD_and_domain_signal_identifies_hotspots",
        ],
    }

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out), "recommendation": recommendation}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
