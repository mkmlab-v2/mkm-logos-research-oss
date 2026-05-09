from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


def _parse_ts(s: Any) -> datetime | None:
    if s is None:
        return None
    t = str(s).strip()
    if not t:
        return None
    try:
        if t.endswith("Z"):
            return datetime.fromisoformat(t.replace("Z", "+00:00"))
        return datetime.fromisoformat(t)
    except ValueError:
        return None


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            out.append(obj)
    return out


def _iso(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


def _simulate_notification_suppression(
    rows_raw: list[dict[str, Any]],
    *,
    window_start: datetime,
    dedupe_window: timedelta,
) -> dict[str, Any]:
    filtered: list[dict[str, Any]] = []
    for r in rows_raw:
        ts = _parse_ts(r.get("ts_utc"))
        if ts is None or ts < window_start:
            continue
        filtered.append(
            {
                "ts": ts,
                "task_name": str(r.get("task_name") or ""),
                "result_category": str(r.get("result_category") or ""),
                "last_task_result": r.get("last_task_result"),
            }
        )
    filtered.sort(key=lambda x: x["ts"])

    by_task: dict[str, list[dict[str, Any]]] = defaultdict(list)
    timeline: dict[datetime, list[dict[str, Any]]] = defaultdict(list)
    for row in filtered:
        timeline[row["ts"]].append(row)

    prev_status = "UNKNOWN"
    prev_signature = ""
    last_sent_at: datetime | None = None
    potential_critical_events = 0
    sent_events = 0
    suppressed_cooldown = 0
    suppressed_same_signature = 0

    for ts in sorted(timeline.keys()):
        batch = timeline[ts]
        for row in batch:
            by_task[row["task_name"]].append(row)

        offenders = []
        for task, arr in by_task.items():
            if len(arr) < 2:
                continue
            last_two = arr[-2:]
            non_ok = [x for x in last_two if x["result_category"] != "OK"]
            if len(non_ok) == 2:
                offenders.append(
                    {
                        "task_name": task,
                        "recent_categories": [x["result_category"] for x in last_two],
                        "recent_codes": [x.get("last_task_result") for x in last_two],
                    }
                )
        offenders.sort(key=lambda x: x["task_name"])
        status = "CRITICAL" if offenders else "PASS"
        signature = json.dumps(offenders, ensure_ascii=False, sort_keys=True)
        if status == "CRITICAL":
            potential_critical_events += 1
            transition_or_changed = (prev_status != "CRITICAL" or prev_signature != signature)
            in_cooldown = bool(last_sent_at is not None and (ts - last_sent_at) < dedupe_window)
            if transition_or_changed and not in_cooldown:
                sent_events += 1
                last_sent_at = ts
            else:
                if in_cooldown:
                    suppressed_cooldown += 1
                else:
                    suppressed_same_signature += 1
        prev_status = status
        prev_signature = signature

    suppression_rate = (
        round(((potential_critical_events - sent_events) / potential_critical_events) * 100.0, 2)
        if potential_critical_events
        else 0.0
    )
    return {
        "potential_critical_events_7d": potential_critical_events,
        "estimated_sent_events_7d": sent_events,
        "suppressed_events_7d": potential_critical_events - sent_events,
        "suppressed_by_cooldown_7d": suppressed_cooldown,
        "suppressed_by_same_signature_7d": suppressed_same_signature,
        "suppression_rate_percent_7d": suppression_rate,
    }


def build() -> int:
    root = Path("C:/workspace")
    reports = root / "reports"
    artifacts = root / "docs" / "final" / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc)
    window_start = now - timedelta(days=7)

    alert_latest = _read_json(artifacts / "core_task_consecutive_failure_alert_latest.json")
    history = _read_jsonl(reports / "core_task_health_history_v1.jsonl")
    rows = []
    for r in history:
        ts = _parse_ts(r.get("ts_utc"))
        if ts is None or ts < window_start:
            continue
        task = str(r.get("task_name") or "")
        cat = str(r.get("result_category") or "")
        rows.append({"ts": ts, "task_name": task, "result_category": cat})
    rows.sort(key=lambda x: (x["task_name"], x["ts"]))

    per_task_total = defaultdict(int)
    per_task_non_ok = defaultdict(int)
    duplicate_bursts = defaultdict(int)
    last_seen: dict[tuple[str, str], datetime] = {}
    dedupe_window = timedelta(minutes=30)

    for row in rows:
        task = str(row["task_name"])
        cat = str(row["result_category"])
        per_task_total[task] += 1
        if cat != "OK":
            per_task_non_ok[task] += 1
            key = (task, cat)
            prev = last_seen.get(key)
            if prev is not None and (row["ts"] - prev) <= dedupe_window:
                duplicate_bursts[task] += 1
            last_seen[key] = row["ts"]

    task_quality = []
    for task in sorted(per_task_total.keys()):
        total = per_task_total[task]
        non_ok = per_task_non_ok.get(task, 0)
        dup = duplicate_bursts.get(task, 0)
        noise_ratio = round((dup / non_ok) * 100.0, 2) if non_ok else 0.0
        task_quality.append(
            {
                "task_name": task,
                "samples_7d": total,
                "non_ok_samples_7d": non_ok,
                "duplicate_bursts_30m_7d": dup,
                "noise_ratio_percent": noise_ratio,
            }
        )

    total_non_ok = sum(per_task_non_ok.values())
    total_dup = sum(duplicate_bursts.values())
    global_noise = round((total_dup / total_non_ok) * 100.0, 2) if total_non_ok else 0.0
    suppression = _simulate_notification_suppression(
        history,
        window_start=window_start,
        dedupe_window=dedupe_window,
    )

    out = {
        "schema": "core_alert_quality_report_v1",
        "generated_at_utc": _iso(now),
        "window": {"start_utc": _iso(window_start), "end_utc": _iso(now), "days": 7},
        "inputs": {
            "alert_latest": "docs/final/artifacts/core_task_consecutive_failure_alert_latest.json",
            "history_jsonl": "reports/core_task_health_history_v1.jsonl",
            "dedupe_window_minutes": 30,
        },
        "current_alert_status": alert_latest.get("status"),
        "quality": {
            "global_non_ok_samples_7d": total_non_ok,
            "global_duplicate_bursts_7d": total_dup,
            "global_noise_ratio_percent": global_noise,
            "notification_suppression_kpi": suppression,
            "tasks": task_quality,
        },
        "recommendations": [
            "Apply 30m cooldown per task/category for repeated non-OK states.",
            "Send webhook only on state transition PASS -> CRITICAL or offender-set change.",
            "Keep full samples in JSONL but suppress duplicate notifications.",
        ],
    }

    out_json = artifacts / "core_alert_quality_report_latest.json"
    out_md = artifacts / "core_alert_quality_report_latest.md"
    out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    out_md.write_text(
        "\n".join(
            [
                "# Core Alert Quality Report",
                "",
                f"- generated_at_utc: `{out['generated_at_utc']}`",
                f"- current_alert_status: `{out['current_alert_status']}`",
                f"- global_non_ok_samples_7d: `{total_non_ok}`",
                f"- global_duplicate_bursts_7d: `{total_dup}`",
                f"- global_noise_ratio_percent: `{global_noise}`",
                f"- suppression_rate_percent_7d: `{suppression['suppression_rate_percent_7d']}`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"wrote: {out_json}")
    print(f"wrote: {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(build())

