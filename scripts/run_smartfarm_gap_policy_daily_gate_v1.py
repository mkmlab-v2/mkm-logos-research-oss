#!/usr/bin/env python3
"""Daily gate runner for smartfarm gap policy recommendation."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run daily GO/WATCH/HOLD gate from recommended gap policy artifact.")
    parser.add_argument(
        "--recommended-policy-json",
        default="data/smartfarm_rda_extract_v1/out/recommended_policy_v1.json",
    )
    parser.add_argument(
        "--guard-summary-json",
        default="data/smartfarm_rda_extract_v1/out/week4_data_guard_summary_v1.json",
    )
    parser.add_argument(
        "--zone-weather-csv",
        default="data/smartfarm_rda_extract_v1/out/zone_weather_features_v1.csv",
        help="Zone weather features used for freshness guard.",
    )
    parser.add_argument(
        "--freshness-reference-json",
        default="",
        help="Optional JSON snapshot path with generated_at_utc to measure ingest freshness.",
    )
    parser.add_argument(
        "--output-json",
        default="data/smartfarm_rda_extract_v1/out/smartfarm_gap_policy_daily_gate_v1.json",
    )
    parser.add_argument(
        "--output-alert-json",
        default="data/smartfarm_rda_extract_v1/out/smartfarm_gap_policy_daily_alert_v1.json",
    )
    parser.add_argument(
        "--output-log-jsonl",
        default="reports/smartfarm_gap_policy_daily_gate_log.jsonl",
    )
    parser.add_argument(
        "--max-allowed-gap-hours",
        type=float,
        default=12.0,
        help="If observed max gap exceeds this, force HOLD.",
    )
    parser.add_argument(
        "--freshness-max-hours",
        type=float,
        default=24.0,
        help="If latest zone data is older than this, downgrade to WATCH.",
    )
    parser.add_argument(
        "--policy-profile-json",
        default="data/smartfarm_rda_extract_v1/out/daily_gate_policy_profile_v1.json",
        help="Optional profile config JSON for mode-based gate thresholds.",
    )
    parser.add_argument(
        "--profile",
        choices=("conservative", "standard", "aggressive"),
        default=None,
        help="Optional policy profile key. If omitted, fallback to profile default then CLI threshold.",
    )
    return parser.parse_args()


def _expect_exists(path: Path) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")
    return path


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _compute_freshness_hours(zone_weather_path: Path, now_utc: datetime) -> float | None:
    if not zone_weather_path.exists():
        return None
    import pandas as pd

    df = pd.read_csv(zone_weather_path, usecols=["agmet_ts_utc"])
    if df.empty:
        return None
    ts = pd.to_datetime(df["agmet_ts_utc"], errors="coerce", utc=True).dropna()
    if ts.empty:
        return None
    latest = ts.max().to_pydatetime()
    return (now_utc - latest).total_seconds() / 3600.0


def _compute_freshness_hours_from_snapshot(snapshot_path: Path, now_utc: datetime) -> float | None:
    if not snapshot_path.exists():
        return None
    payload = _load_json(snapshot_path)
    generated_at = payload.get("generated_at_utc")
    if not isinstance(generated_at, str) or not generated_at.strip():
        return None
    snap_dt = datetime.fromisoformat(generated_at.replace("Z", "+00:00")).astimezone(UTC)
    return (now_utc - snap_dt).total_seconds() / 3600.0


def main() -> int:
    args = _parse_args()
    rec_path = _expect_exists(Path(args.recommended_policy_json))
    guard_path = _expect_exists(Path(args.guard_summary_json))
    out_path = Path(args.output_json)
    out_alert = Path(args.output_alert_json)
    out_log = Path(args.output_log_jsonl)
    _ensure_parent(out_path)
    _ensure_parent(out_alert)
    _ensure_parent(out_log)

    rec = _load_json(rec_path)
    guard = _load_json(guard_path)

    now_dt = datetime.now(UTC)
    now = now_dt.isoformat()
    recommended = rec.get("recommendation", "flag_only")
    guard_status = guard.get("status", "UNKNOWN")
    checks = guard.get("checks", {})
    max_gap = float(checks.get("time_gap", {}).get("max_gap_hours", 0.0))

    selected_profile = None
    selected_profile_threshold = None
    selected_profile_incident_watch_cap = None
    selected_profile_gap_watch_cap = None
    selected_profile_cfg: dict | None = None
    profile_path = Path(args.policy_profile_json)
    if profile_path.exists():
        profile_cfg = _load_json(profile_path)
        profiles = profile_cfg.get("profiles", {})
        profile_key = args.profile or profile_cfg.get("default_profile")
        if profile_key in profiles:
            selected_profile = profile_key
            selected_profile_cfg = profiles[profile_key]
            selected_profile_threshold = float(
                selected_profile_cfg.get("max_allowed_gap_hours", args.max_allowed_gap_hours)
            )
            if "max_incident_count_for_watch" in selected_profile_cfg:
                selected_profile_incident_watch_cap = int(selected_profile_cfg["max_incident_count_for_watch"])
            if "max_gap_hours_for_watch_override" in selected_profile_cfg:
                selected_profile_gap_watch_cap = float(selected_profile_cfg["max_gap_hours_for_watch_override"])

    effective_max_gap = (
        selected_profile_threshold
        if selected_profile_threshold is not None
        else args.max_allowed_gap_hours
    )
    large_gap_incident_count = int(checks.get("time_gap", {}).get("large_gap_count", 0))

    decision = "WATCH"
    reasons: list[str] = []

    if max_gap > effective_max_gap:
        decision = "HOLD"
        reasons.append(
            f"time_gap_exceeds_limit(max_gap_hours={max_gap}, limit={effective_max_gap})"
        )
        # Optional profile-based HOLD->WATCH downgrade for exploratory mode.
        if (
            selected_profile_incident_watch_cap is not None
            and selected_profile_gap_watch_cap is not None
            and large_gap_incident_count <= selected_profile_incident_watch_cap
            and max_gap <= selected_profile_gap_watch_cap
        ):
            decision = "WATCH"
            reasons.append(
                "profile_watch_override("
                f"max_gap_hours<={selected_profile_gap_watch_cap},"
                f"large_gap_count<={selected_profile_incident_watch_cap})"
            )
    elif guard_status != "PASS":
        decision = "WATCH"
        reasons.append(f"guard_status={guard_status}")
    elif recommended == "hybrid_skip_large_ffill_small":
        decision = "GO"
        reasons.append("guard_pass_and_recommendation_hybrid")
    elif recommended == "skip":
        decision = "WATCH"
        reasons.append("recommendation_skip_safety_first")
    else:
        decision = "HOLD"
        reasons.append(f"recommendation={recommended}")

    # Freshness guard: stale data cannot be GO.
    freshness_source = "zone_weather_csv"
    freshness_hours = _compute_freshness_hours(Path(args.zone_weather_csv), now_dt)
    if args.freshness_reference_json.strip():
        snapshot_hours = _compute_freshness_hours_from_snapshot(Path(args.freshness_reference_json), now_dt)
        if snapshot_hours is not None:
            freshness_hours = snapshot_hours
            freshness_source = "freshness_reference_json"
    if freshness_hours is not None and freshness_hours > args.freshness_max_hours:
        if decision == "GO":
            decision = "WATCH"
        reasons.append(
            f"freshness_stale(hours={round(freshness_hours, 2)}, max={args.freshness_max_hours})"
        )

    payload = {
        "schema": "smartfarm_gap_policy_daily_gate_v1",
        "generated_at_utc": now,
        "decision": decision,
        "recommended_policy": recommended,
        "guard_status": guard_status,
        "max_gap_hours_observed": max_gap,
        "large_gap_incident_count": large_gap_incident_count,
        "max_allowed_gap_hours": effective_max_gap,
        "profile": selected_profile,
        "profile_watch_override_caps": {
            "max_incident_count_for_watch": selected_profile_incident_watch_cap,
            "max_gap_hours_for_watch_override": selected_profile_gap_watch_cap,
        },
        "freshness": {
            "source": freshness_source,
            "zone_weather_csv": args.zone_weather_csv,
            "freshness_reference_json": args.freshness_reference_json if args.freshness_reference_json else None,
            "freshness_hours": freshness_hours,
            "freshness_max_hours": args.freshness_max_hours,
        },
        "reasons": reasons,
        "references": {
            "recommended_policy_json": str(rec_path),
            "guard_summary_json": str(guard_path),
            "policy_profile_json": str(profile_path) if profile_path.exists() else None,
        },
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    alert = {
        "schema": "smartfarm_gap_policy_daily_alert_v1",
        "generated_at_utc": now,
        "severity": "critical" if decision == "HOLD" else ("warning" if decision == "WATCH" else "info"),
        "title": f"Smartfarm Gap Policy Daily Gate: {decision}",
        "message": "; ".join(reasons),
        "decision_payload_path": str(out_path),
    }
    out_alert.write_text(json.dumps(alert, ensure_ascii=False, indent=2), encoding="utf-8")

    with out_log.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")

    print(f"[ok] daily gate -> {out_path}")
    print(f"[ok] alert payload -> {out_alert}")
    print(f"[ok] decision={decision}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

