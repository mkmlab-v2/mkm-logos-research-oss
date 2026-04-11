#!/usr/bin/env python3
"""Build quality alert artifact for report_schema_v2 monitoring."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_KPI = ROOT / "docs" / "final" / "artifacts" / "report_schema_v2_label_kpi_latest.json"
DEFAULT_LOG = ROOT / "docs" / "final" / "artifacts" / "waiting_queue_monthly_check_log.jsonl"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "report_schema_v2_quality_alert_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def _latest_jsonl(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    lines = [x for x in path.read_text(encoding="utf-8", errors="ignore").splitlines() if x.strip()]
    for line in reversed(lines):
        try:
            obj = json.loads(line)
            if isinstance(obj, dict):
                return obj
        except Exception:
            continue
    return {}


def _float_or_none(raw: Any) -> float | None:
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def compute_v2_quality_severity(
    *,
    grounded_false_rate: Any,
    gate: Any,
    streak_alert: bool,
    fail_solo_grounded_false_rate: float,
    fail_pair_min_grounded_false_rate: float,
    fail_on_streak_and_gate_warn: bool,
    warn_min_grounded_false_rate: float,
) -> tuple[str, list[str]]:
    """Return (severity, reason_codes) with severity in INFO | WARN | FAIL."""
    gfr = _float_or_none(grounded_false_rate)
    gate_warn = str(gate or "").lower() == "warn"
    fail_reasons: list[str] = []

    if fail_on_streak_and_gate_warn and streak_alert and gate_warn:
        fail_reasons.append("fail_delta_streak_and_label_kpi_gate_warn")
    if streak_alert and gfr is not None and gfr >= fail_pair_min_grounded_false_rate:
        fail_reasons.append("fail_delta_streak_with_grounded_false_rate_ge_pair_min")
    if gfr is not None and gfr >= fail_solo_grounded_false_rate:
        fail_reasons.append("fail_grounded_false_rate_ge_solo_ceiling")

    if fail_reasons:
        return "FAIL", fail_reasons

    warn_reasons: list[str] = []
    if gate_warn:
        warn_reasons.append("warn_label_kpi_gate")
    if streak_alert:
        warn_reasons.append("warn_delta_streak_alert")
    if gfr is not None and gfr >= warn_min_grounded_false_rate:
        warn_reasons.append("warn_grounded_false_rate_ge_threshold")

    if warn_reasons:
        return "WARN", warn_reasons

    return "INFO", []


def main() -> int:
    parser = argparse.ArgumentParser(description="Build report_schema_v2 quality alert artifact.")
    parser.add_argument("--kpi", default=str(DEFAULT_KPI))
    parser.add_argument("--log", default=str(DEFAULT_LOG))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument(
        "--fail-solo-grounded-false-rate",
        type=float,
        default=float(os.getenv("FACT_SAFE_V2_QUALITY_FAIL_SOLO_GFR", "0.25")),
        help="FAIL if grounded_false_rate >= this (solo ceiling).",
    )
    parser.add_argument(
        "--fail-pair-min-grounded-false-rate",
        type=float,
        default=float(os.getenv("FACT_SAFE_V2_QUALITY_FAIL_PAIR_MIN_GFR", "0.10")),
        help="FAIL if delta_streak_alert and grounded_false_rate >= this (pair rule).",
    )
    parser.add_argument(
        "--warn-min-grounded-false-rate",
        type=float,
        default=float(os.getenv("FACT_SAFE_V2_QUALITY_WARN_MIN_GFR", "0.08")),
        help="WARN if grounded_false_rate >= this (and not already FAIL).",
    )
    fail_streak_gate_default = os.getenv("FACT_SAFE_V2_QUALITY_FAIL_STREAK_AND_GATE", "1").strip().lower() in {
        "1",
        "true",
        "yes",
    }
    parser.add_argument(
        "--fail-on-streak-and-gate-warn",
        action=argparse.BooleanOptionalAction,
        default=fail_streak_gate_default,
        help="FAIL when delta_streak_alert and label_kpi_gate warn both true.",
    )
    args = parser.parse_args()

    kpi_path = Path(args.kpi)
    log_path = Path(args.log)
    out_path = Path(args.out)

    kpi = _load_json(kpi_path)
    latest = _latest_jsonl(log_path)

    grounded_false_rate = ((kpi.get("totals") or {}).get("grounded_false_rate"))
    label_distribution = kpi.get("label_distribution") if isinstance(kpi.get("label_distribution"), dict) else {}
    streak_alert = bool(latest.get("report_schema_v2_grounded_false_rate_delta_streak_alert", False))
    streak = latest.get("report_schema_v2_grounded_false_rate_delta_up_streak")
    streak_threshold = latest.get("report_schema_v2_grounded_false_rate_delta_up_streak_threshold")
    gate = latest.get("report_schema_v2_label_kpi_gate")

    severity, reason_codes = compute_v2_quality_severity(
        grounded_false_rate=grounded_false_rate,
        gate=gate,
        streak_alert=streak_alert,
        fail_solo_grounded_false_rate=float(args.fail_solo_grounded_false_rate),
        fail_pair_min_grounded_false_rate=float(args.fail_pair_min_grounded_false_rate),
        fail_on_streak_and_gate_warn=bool(args.fail_on_streak_and_gate_warn),
        warn_min_grounded_false_rate=float(args.warn_min_grounded_false_rate),
    )

    payload = {
        "schema": "report_schema_v2_quality_alert_v1",
        "generated_at_utc": _utc_now(),
        "source_kpi_path": str(kpi_path),
        "source_log_path": str(log_path),
        "thresholds": {
            "fail_solo_grounded_false_rate": float(args.fail_solo_grounded_false_rate),
            "fail_pair_min_grounded_false_rate": float(args.fail_pair_min_grounded_false_rate),
            "warn_min_grounded_false_rate": float(args.warn_min_grounded_false_rate),
            "fail_on_streak_and_gate_warn": bool(args.fail_on_streak_and_gate_warn),
        },
        "status": {
            "severity": severity,
            "reason_codes": reason_codes,
            "delta_streak_alert": streak_alert,
            "gate": gate,
        },
        "metrics": {
            "grounded_false_rate": grounded_false_rate,
            "delta_up_streak": streak,
            "delta_up_streak_threshold": streak_threshold,
            "label_distribution": label_distribution,
        },
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
