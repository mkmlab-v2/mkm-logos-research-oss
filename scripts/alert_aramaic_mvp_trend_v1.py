#!/usr/bin/env python3
"""Evaluate consecutive high-conflict audit tail rows; write alert JSON; optional webhook."""

from __future__ import annotations

import argparse
import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_audit_rows(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
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


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        o = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return o if isinstance(o, dict) else {}


def _conflict_ratio(row: dict[str, Any]) -> float | None:
    if "conflict_ratio" not in row:
        return None
    try:
        return float(row["conflict_ratio"])
    except (TypeError, ValueError):
        return None


def _row_level(
    row: dict[str, Any],
    alert_thr: float,
    critical_thr: float,
) -> int:
    """0 ok, 1 alert, 2 critical (conflict_ratio only for v1)."""
    cr = _conflict_ratio(row)
    if cr is None:
        return 0
    if cr >= critical_thr:
        return 2
    if cr >= alert_thr:
        return 1
    return 0


def _streak_from_newest(levels_newest_first: list[int]) -> tuple[int, int]:
    """Return (streak_len, max_level_in_streak) for consecutive level>=1 from index 0."""
    streak = 0
    max_lv = 0
    for lv in levels_newest_first:
        if lv < 1:
            break
        streak += 1
        max_lv = max(max_lv, lv)
    return streak, max_lv


def evaluate_audit_tail_for_thresholds(
    tail: list[dict[str, Any]],
    *,
    alert_thr: float,
    critical_thr: float,
    streak_min: int,
) -> dict[str, Any]:
    """Same streak/severity rules as CLI; `tail` is chronological (oldest first)."""
    if critical_thr <= alert_thr:
        raise ValueError("conflict-critical must be > conflict-alert")
    sm = max(1, int(streak_min))
    levels = [_row_level(r, alert_thr, critical_thr) for r in reversed(tail)]
    streak_len, max_in_streak = _streak_from_newest(levels)
    severity = "ok"
    if streak_len >= sm and max_in_streak >= 2:
        severity = "critical"
    elif streak_len >= sm:
        severity = "alert"
    return {
        "severity": severity,
        "streak_len": streak_len,
        "max_level_in_streak": max_in_streak,
    }


def _post_webhook(url: str, payload: dict[str, Any]) -> tuple[bool, str]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            code = int(getattr(resp, "status", 0) or 0)
            return 200 <= code < 300, f"http_status={code}"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--audit-jsonl",
        default="reports/ops/aramaic_mvp_run_audit_log.jsonl",
        help="Append-only audit log (same source as report_aramaic_mvp_audit_trend_v1)",
    )
    ap.add_argument(
        "--trend-json",
        default="docs/final/artifacts/aramaic_mvp_audit_trend_latest.json",
        help="Optional trend artifact (metadata only; may be missing)",
    )
    ap.add_argument(
        "--output-json",
        default="docs/final/artifacts/aramaic_mvp_trend_alert_latest.json",
        help="Alert summary JSON",
    )
    ap.add_argument("--window", type=int, default=50, help="Tail rows to scan (default 50)")
    ap.add_argument("--streak-min", type=int, default=3, help="Min consecutive hot rows for alert/critical (default 3)")
    ap.add_argument(
        "--conflict-alert",
        type=float,
        default=0.12,
        help="conflict_ratio >= this counts as alert (default 0.12)",
    )
    ap.add_argument(
        "--conflict-critical",
        type=float,
        default=0.28,
        help="conflict_ratio >= this counts as critical (default 0.28)",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Never POST webhook even if URL is set",
    )
    a = ap.parse_args()

    audit_path = Path(a.audit_jsonl)
    if not audit_path.is_absolute():
        audit_path = ROOT / audit_path
    trend_path = Path(a.trend_json)
    if not trend_path.is_absolute():
        trend_path = ROOT / trend_path
    out_path = Path(a.output_json)
    if not out_path.is_absolute():
        out_path = ROOT / out_path

    window_n = max(1, int(a.window))
    streak_min = max(1, int(a.streak_min))
    alert_thr = float(a.conflict_alert)
    critical_thr = float(a.conflict_critical)
    if critical_thr <= alert_thr:
        raise SystemExit("conflict-critical must be > conflict-alert")

    all_rows = _load_audit_rows(audit_path)
    tail = all_rows[-window_n:] if all_rows else []
    ev = evaluate_audit_tail_for_thresholds(
        tail,
        alert_thr=alert_thr,
        critical_thr=critical_thr,
        streak_min=streak_min,
    )
    streak_len = int(ev["streak_len"])
    max_in_streak = int(ev["max_level_in_streak"])
    severity = str(ev["severity"])

    trend_meta = _load_json(trend_path)
    trend_ref = {
        "path": str(trend_path),
        "schema": trend_meta.get("schema"),
        "generated_at_utc": trend_meta.get("generated_at_utc"),
    } if trend_meta else {"path": str(trend_path), "present": False}

    doc: dict[str, Any] = {
        "schema": "aramaic_mvp_trend_alert_v1",
        "generated_at_utc": _now_utc(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "B",
        "source": {"audit_jsonl": str(audit_path), "trend_json": trend_ref},
        "inputs": {
            "window_requested": window_n,
            "rows_in_tail": len(tail),
            "total_valid_rows_in_file": len(all_rows),
        },
        "thresholds": {
            "conflict_alert": alert_thr,
            "conflict_critical": critical_thr,
            "streak_min": streak_min,
        },
        "streak": {
            "length": streak_len,
            "max_level_in_streak": max_in_streak,
            "from_newest": True,
        },
        "severity": severity,
        "webhook": {"sent": False, "status": "skipped"},
    }

    webhook_url = (os.getenv("ARAMAIC_MVP_ALERT_WEBHOOK_URL") or os.getenv("OPS_ALARM_WEBHOOK_URL") or "").strip()
    if a.dry_run:
        doc["webhook"]["status"] = "skipped_dry_run"
    elif severity == "ok":
        doc["webhook"]["status"] = "skipped_severity_ok"
    elif not webhook_url:
        doc["webhook"]["status"] = "skipped_no_url"
    else:
        payload = {
            "event": "aramaic_mvp_trend_alert_v1",
            "generated_at_utc": doc["generated_at_utc"],
            "severity": severity,
            "streak": doc["streak"],
            "audit_jsonl": str(audit_path),
        }
        ok, status = _post_webhook(webhook_url, payload)
        doc["webhook"] = {"sent": ok, "status": status, "url_present": True}

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
