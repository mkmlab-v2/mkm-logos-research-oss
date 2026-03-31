#!/usr/bin/env python3
"""Non-blocking warning check for run index alert profile."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INDEX = ROOT / "reports" / "constitution" / "btrack_pilot" / "symbol_c_validation_run_index_latest.json"
DEFAULT_WARN_TEMPLATE = (
    ROOT / "data" / "logos" / "btrack_pilot" / "gates" / "symbol_c_validation_strict_warn_template.json"
)
DEFAULT_DELTA_ALERT_LOG = ROOT / "reports" / "constitution" / "btrack_pilot" / "delta_alert_log.jsonl"


def _abs(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def _jread(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _as_float(v: Any) -> float | None:
    if isinstance(v, (int, float)):
        return float(v)
    return None


def _latest_overlap_delta_from_index(idx: dict[str, Any]) -> float | None:
    trend = idx.get("trend", {})
    points = trend.get("points", []) if isinstance(trend, dict) else []
    if not isinstance(points, list) or len(points) < 2:
        return None
    last = points[-1]
    prev = points[-2]
    if not isinstance(last, dict) or not isinstance(prev, dict):
        return None
    l = _as_float(last.get("top_overlap_rate"))
    p = _as_float(prev.get("top_overlap_rate"))
    if l is None or p is None:
        return None
    return l - p


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _resolve_rotated_log_path(base_path: Path, rotate_daily: bool, now_utc: datetime) -> Path:
    if not rotate_daily:
        return base_path
    date_tag = now_utc.strftime("%Y%m%d")
    stem = base_path.stem
    suffix = base_path.suffix or ".jsonl"
    return base_path.with_name(f"{stem}_{date_tag}{suffix}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Warn-only run index alert profile check")
    ap.add_argument("--run-index-json", default=str(DEFAULT_INDEX))
    ap.add_argument("--alert-profile", default="strict")
    ap.add_argument("--warn-template", default=str(DEFAULT_WARN_TEMPLATE))
    ap.add_argument("--delta-alert-log", default=str(DEFAULT_DELTA_ALERT_LOG))
    ap.add_argument("--delta-alert-log-rotate-daily", action="store_true")
    args = ap.parse_args()

    index_path = _abs(args.run_index_json)
    alert_profile = str(args.alert_profile).strip().lower() or "strict"
    if not index_path.is_file():
        print(f"WARN: missing run index: {index_path}")
        return 0

    idx = _jread(index_path)
    warn_threshold = -0.05
    warn_template_path = _abs(args.warn_template)
    if warn_template_path.is_file():
        cfg = _jread(warn_template_path)
        warn_threshold = float(cfg.get("overlap_delta_warn_threshold", warn_threshold))
    profiles = idx.get("alert_profiles", {})
    alert = profiles.get(alert_profile, {}) if isinstance(profiles, dict) else {}
    decision = str(alert.get("decision", "hold")).lower()
    failures = alert.get("failures", [])

    print("Symbol C validation run index alert warning")
    print(f"- profile: {alert_profile}")
    print(f"- decision: {decision}")
    delta = _latest_overlap_delta_from_index(idx)
    print(f"- latest_delta_vs_prev_overlap: {delta}")
    if delta is not None and delta <= warn_threshold:
        print(f"WARN: overlap delta below threshold ({delta} <= {warn_threshold})")
        now_utc = datetime.now(timezone.utc)
        log_path = _resolve_rotated_log_path(
            _abs(args.delta_alert_log), args.delta_alert_log_rotate_daily, now_utc
        )
        _append_jsonl(
            log_path,
            {
                "ts_utc": now_utc.isoformat(),
                "profile": alert_profile,
                "decision": decision,
                "delta": delta,
                "threshold": warn_threshold,
                "run_index_json": str(index_path),
            },
        )
        print(f"WARN: delta alert logged path={log_path}")
    if decision != "pass":
        print("WARN: strict profile indicates hold")
        if isinstance(failures, list):
            for f in failures:
                print(f"- {f}")
    else:
        print("OK: strict profile pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
