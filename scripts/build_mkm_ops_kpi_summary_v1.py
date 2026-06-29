#!/usr/bin/env python3
"""Build weekly KPI summary from MKM command package paste logs."""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG = ROOT / "reports" / "mkm_command_package_paste_log.jsonl"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "mkm_ops_kpi_summary_v1_latest.json"


def _parse_dt(value: str) -> datetime | None:
    # PowerShell "o" can emit 7 fractional digits; Python expects <=6.
    if "." in value:
        head, tail = value.split(".", 1)
        tz_split = tail.find("+")
        if tz_split < 0:
            tz_split = tail.find("-")
        if tz_split > 0:
            frac = tail[:tz_split]
            rest = tail[tz_split:]
            value = f"{head}.{frac[:6]}{rest}"
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _load_rows(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            try:
                obj = json.loads(s)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                rows.append(obj)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--log-jsonl", type=Path, default=DEFAULT_LOG)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--window-days", type=int, default=7)
    args = ap.parse_args()

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=max(1, args.window_days))
    rows = _load_rows(args.log_jsonl)

    in_window: list[dict[str, Any]] = []
    for row in rows:
        ts = _parse_dt(str(row.get("generated_at_local") or ""))
        if ts is None:
            continue
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        ts_utc = ts.astimezone(timezone.utc)
        if ts_utc >= cutoff:
            in_window.append(row)

    pkg_counter: Counter[str] = Counter()
    step_fail_counter: Counter[str] = Counter()
    optional_fail_total = 0
    process_fail_count = 0
    in_window.sort(key=lambda row: str(row.get("generated_at_local") or ""))

    failure_windows: list[dict[str, Any]] = []
    open_failures: dict[str, datetime] = {}
    prev_ts_utc: datetime | None = None
    run_interval_hours: list[float] = []

    for row in in_window:
        ts = _parse_dt(str(row.get("generated_at_local") or ""))
        if ts is None:
            continue
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        ts_utc = ts.astimezone(timezone.utc)

        if prev_ts_utc is not None:
            delta_h = (ts_utc - prev_ts_utc).total_seconds() / 3600.0
            if delta_h >= 0:
                run_interval_hours.append(delta_h)
        prev_ts_utc = ts_utc

        pkg = str(row.get("package") or "unknown")
        pkg_counter[pkg] += 1
        optional_fail_total += int(row.get("optional_fail_count") or 0)
        has_fail = int(row.get("process_exit_code") or 0) != 0
        if has_fail:
            process_fail_count += 1
            for step in row.get("steps") or []:
                if not isinstance(step, dict):
                    continue
                step_id = str(step.get("id") or "unknown")
                if int(step.get("exit_code") or 0) != 0 and step_id not in open_failures:
                    open_failures[step_id] = ts_utc
        else:
            for step in row.get("steps") or []:
                if not isinstance(step, dict):
                    continue
                step_id = str(step.get("id") or "unknown")
                if int(step.get("exit_code") or 0) == 0 and step_id in open_failures:
                    started_at = open_failures.pop(step_id)
                    mttr_h = (ts_utc - started_at).total_seconds() / 3600.0
                    if mttr_h >= 0:
                        failure_windows.append(
                            {
                                "step_id": step_id,
                                "failure_started_at_utc": started_at.isoformat().replace("+00:00", "Z"),
                                "recovered_at_utc": ts_utc.isoformat().replace("+00:00", "Z"),
                                "recovery_hours": round(mttr_h, 6),
                            }
                        )

        for step in row.get("steps") or []:
            if not isinstance(step, dict):
                continue
            if int(step.get("exit_code") or 0) != 0:
                step_fail_counter[str(step.get("id") or "unknown")] += 1

    total_runs = len(in_window)
    pass_runs = total_runs - process_fail_count
    pass_rate = (pass_runs / total_runs) if total_runs else 0.0
    warn_or_fail_run_rate = (process_fail_count / total_runs) if total_runs else 0.0
    mean_optional_fail = (optional_fail_total / total_runs) if total_runs else 0.0
    mean_run_interval_h = (sum(run_interval_hours) / len(run_interval_hours)) if run_interval_hours else None
    mttr_hours = [float(x["recovery_hours"]) for x in failure_windows]
    mean_mttr_h = (sum(mttr_hours) / len(mttr_hours)) if mttr_hours else None
    median_mttr_h = None
    if mttr_hours:
        sorted_mttr = sorted(mttr_hours)
        mid = len(sorted_mttr) // 2
        if len(sorted_mttr) % 2 == 0:
            median_mttr_h = (sorted_mttr[mid - 1] + sorted_mttr[mid]) / 2.0
        else:
            median_mttr_h = sorted_mttr[mid]

    out: dict[str, Any] = {
        "schema": "mkm_ops_kpi_summary_v1",
        "generated_at_utc": now.isoformat().replace("+00:00", "Z"),
        "window_days": max(1, args.window_days),
        "source_log": str(args.log_jsonl),
        "totals": {
            "runs": total_runs,
            "pass_runs": pass_runs,
            "warn_or_fail_runs": process_fail_count,
            "pass_rate": round(pass_rate, 6),
            "warn_or_fail_run_rate": round(warn_or_fail_run_rate, 6),
            "mean_optional_fail_count": round(mean_optional_fail, 6),
        },
        "poc_proxy_kpis": {
            "mean_run_interval_hours": round(mean_run_interval_h, 6) if mean_run_interval_h is not None else None,
            "detection_latency_proxy_hours": round(mean_run_interval_h, 6) if mean_run_interval_h is not None else None,
            "auto_recovery_mean_hours": round(mean_mttr_h, 6) if mean_mttr_h is not None else None,
            "auto_recovery_median_hours": round(median_mttr_h, 6) if median_mttr_h is not None else None,
            "recovered_failure_windows": len(failure_windows),
            "open_failure_steps": sorted(open_failures.keys()),
            "definition_note": "MTTD proxy=mean interval between patrol runs; MTTR proxy=hours from first failed step occurrence to next observed pass for same step.",
        },
        "package_counts": dict(pkg_counter),
        "top_failed_steps": [
            {"step_id": step_id, "count": count}
            for step_id, count in step_fail_counter.most_common(10)
        ],
        "recovery_windows_sample": failure_windows[:20],
        "ops_readme": {
            "kpi_note": "Use PoC-measured deltas only for external ROI claims.",
            "track_wall": "research_only; no Track A/live auto-promotion",
        },
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "runs": total_runs, "out": str(args.out_json)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
