from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


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


def _parse_ts(v: Any) -> datetime | None:
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    try:
        if s.endswith("Z"):
            return datetime.fromisoformat(s.replace("Z", "+00:00"))
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def _iso(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


def build() -> int:
    root = Path("C:/workspace")
    reports = root / "reports"
    art = root / "docs" / "final" / "artifacts"
    art.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc)
    start = now - timedelta(days=7)
    rows = []
    for r in _read_jsonl(reports / "core_task_health_history_v1.jsonl"):
        ts = _parse_ts(r.get("ts_utc"))
        if ts is None or ts < start:
            continue
        rows.append(
            {
                "ts": ts,
                "task_name": str(r.get("task_name") or ""),
                "cat": str(r.get("result_category") or ""),
            }
        )

    rows.sort(key=lambda x: (x["task_name"], x["ts"]))
    # Approximate RTO: first non-OK to next OK for each task.
    rto_minutes: list[float] = []
    recoveries: list[dict[str, Any]] = []
    by_task: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_task.setdefault(str(row["task_name"]), []).append(row)

    for task, arr in by_task.items():
        fail_ts: datetime | None = None
        for e in arr:
            if e["cat"] != "OK" and fail_ts is None:
                fail_ts = e["ts"]
            elif e["cat"] == "OK" and fail_ts is not None:
                mins = (e["ts"] - fail_ts).total_seconds() / 60.0
                if mins >= 0:
                    rto_minutes.append(mins)
                    recoveries.append(
                        {
                            "task_name": task,
                            "failed_at_utc": _iso(fail_ts),
                            "recovered_at_utc": _iso(e["ts"]),
                            "rto_minutes": round(mins, 2),
                        }
                    )
                fail_ts = None

    rto_avg = round(sum(rto_minutes) / len(rto_minutes), 2) if rto_minutes else None
    rto_max = round(max(rto_minutes), 2) if rto_minutes else None

    out = {
        "schema": "recovery_rto_drill_report_v1",
        "generated_at_utc": _iso(now),
        "window": {"start_utc": _iso(start), "end_utc": _iso(now), "days": 7},
        "recovery_summary": {
            "recovery_events": len(recoveries),
            "rto_avg_minutes": rto_avg,
            "rto_max_minutes": rto_max,
            "rto_target_minutes": 120,
            "rto_target_met": (rto_max is not None and rto_max <= 120),
        },
        "recoveries": recoveries[-20:],
        "recommendations": [
            "Keep bootstrap/fallback chain to reduce fail-to-recover window.",
            "For recurrent failures, alert only on first transition and on unresolved >120m.",
        ],
        "evidence": {
            "core_task_history_jsonl": "reports/core_task_health_history_v1.jsonl",
        },
    }

    out_json = art / "recovery_rto_drill_report_latest.json"
    out_md = art / "recovery_rto_drill_report_latest.md"
    out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    out_md.write_text(
        "\n".join(
            [
                "# Recovery RTO Drill Report",
                "",
                f"- generated_at_utc: `{out['generated_at_utc']}`",
                f"- recovery_events: `{out['recovery_summary']['recovery_events']}`",
                f"- rto_avg_minutes: `{out['recovery_summary']['rto_avg_minutes']}`",
                f"- rto_max_minutes: `{out['recovery_summary']['rto_max_minutes']}`",
                f"- rto_target_met: `{out['recovery_summary']['rto_target_met']}`",
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

