#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_now_str() -> str:
    return utc_now().isoformat().replace("+00:00", "Z")


def resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def parse_utc(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def append_jsonl(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(row, ensure_ascii=False)
    with path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def read_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description="Alert when Track C stays WATCH for too long.")
    ap.add_argument("--dashboard-json", default="docs/final/artifacts/mkm_trackc_ops_dashboard_latest.json")
    ap.add_argument("--kpi-contract-json", default="docs/final/artifacts/mkm_trackc_watch_exit_kpi_contract_latest.json")
    ap.add_argument("--state-log-jsonl", default="reports/mkm_trackc_watch_state_log.jsonl")
    ap.add_argument("--output-json", default="docs/final/artifacts/mkm_trackc_watch_prolonged_alert_latest.json")
    ap.add_argument("--default-threshold-days", type=int, default=14)
    args = ap.parse_args()

    p_dash = resolve(args.dashboard_json)
    p_kpi = resolve(args.kpi_contract_json)
    p_log = resolve(args.state_log_jsonl)
    p_out = resolve(args.output_json)
    if not p_dash.is_file():
        raise SystemExit(f"missing dashboard json: {p_dash}")

    dashboard = load_json(p_dash)
    decision_state = str(dashboard.get("trackc", {}).get("api_decision_state", "UNKNOWN"))
    guard_passed = bool(dashboard.get("trackc", {}).get("guard_passed", False))

    threshold_days = args.default_threshold_days
    if p_kpi.is_file():
        kpi = load_json(p_kpi)
        threshold_days = int(
            kpi.get("watch_exit_kpis", {}).get("max_watch_days_without_recheck", threshold_days)
        )

    now = utc_now()
    today = now.date().isoformat()
    append_jsonl(
        p_log,
        {
            "schema": "mkm_trackc_watch_state_log_v1",
            "recorded_at_utc": utc_now_str(),
            "recorded_date_utc": today,
            "decision_state": decision_state,
            "guard_passed": guard_passed,
            "dashboard_ref": str(p_dash),
        },
    )

    rows = read_jsonl(p_log)
    # Keep only the latest state for each day.
    latest_by_day: dict[str, dict] = {}
    for row in rows:
        d = str(row.get("recorded_date_utc", ""))
        t = str(row.get("recorded_at_utc", ""))
        if not d:
            continue
        prev = latest_by_day.get(d)
        if prev is None or t > str(prev.get("recorded_at_utc", "")):
            latest_by_day[d] = row

    days = sorted(latest_by_day.keys())
    watch_streak = 0
    for d in reversed(days):
        state = str(latest_by_day[d].get("decision_state", "UNKNOWN"))
        if state == "WATCH":
            watch_streak += 1
        else:
            break

    alert = watch_streak >= threshold_days
    status = "ALERT_PROLONGED_WATCH" if alert else "OK"
    payload = {
        "schema": "mkm_trackc_watch_prolonged_alert_v1",
        "generated_at_utc": utc_now_str(),
        "status": status,
        "decision_state": decision_state,
        "watch_streak_days": watch_streak,
        "threshold_days": threshold_days,
        "alert": alert,
        "next_action": (
            "Trigger re-evaluation and human review immediately."
            if alert
            else "Continue conservative guard monitoring."
        ),
        "refs": {
            "dashboard_json": str(p_dash),
            "kpi_contract_json": str(p_kpi),
            "state_log_jsonl": str(p_log),
        },
    }
    p_out.parent.mkdir(parents=True, exist_ok=True)
    p_out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(p_out))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
