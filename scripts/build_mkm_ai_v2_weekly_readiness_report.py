from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build weekly readiness summary from MKM AI v2 daily logs."
    )
    parser.add_argument(
        "--workspace-root",
        default="C:/workspace",
        help="Workspace root path (default: C:/workspace)",
    )
    parser.add_argument(
        "--window-days",
        type=int,
        default=7,
        help="Rolling window size in days (default: 7)",
    )
    return parser.parse_args()


def _norm_ts_key(ts: str) -> Optional[str]:
    dt = _parse_utc(ts)
    if dt is None:
        return None
    return dt.isoformat().replace("+00:00", "Z")


def _load_weekly_exclusions(
    root: Path,
) -> Tuple[List[str], Dict[str, str]]:
    """
    Optional audited exclusions (rolling-window stats only; raw JSONL unchanged).

    Search order (first existing wins):
      scripts/mkm_ai_v2_weekly_readiness_exclusions_v1.json (tracked policy default)
      docs/final/artifacts/mkm_ai_v2_weekly_readiness_exclusions_v1.json (optional override)

    Schema: { "schema", "exclusions": [ { "ts_utc", "reason" } ] }
    """
    candidates = [
        root / "scripts" / "mkm_ai_v2_weekly_readiness_exclusions_v1.json",
        root / "docs" / "final" / "artifacts" / "mkm_ai_v2_weekly_readiness_exclusions_v1.json",
    ]
    path = next((p for p in candidates if p.exists()), None)
    if path is None:
        return [], {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return [], {}
    if not isinstance(raw, dict):
        return [], {}
    reasons: Dict[str, str] = {}
    keys: List[str] = []
    for item in raw.get("exclusions") or []:
        if not isinstance(item, dict):
            continue
        ts = str(item.get("ts_utc", "")).strip()
        rk = _norm_ts_key(ts)
        if rk is None:
            continue
        keys.append(rk)
        r = str(item.get("reason", "")).strip()
        if r:
            reasons[rk] = r
    # de-dupe preserve order
    seen = set()
    uniq: List[str] = []
    for k in keys:
        if k in seen:
            continue
        seen.add(k)
        uniq.append(k)
    return uniq, reasons


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    rows: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def _parse_utc(ts: str) -> datetime | None:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def main() -> int:
    args = _parse_args()
    root = Path(args.workspace_root)
    log_path = root / "reports" / "mkm_ai_v2_readiness_log.jsonl"
    out_path = root / "docs" / "final" / "artifacts" / "mkm_ai_v2_weekly_readiness_report_latest.json"

    now = datetime.now(timezone.utc)
    window_start = now - timedelta(days=max(args.window_days, 1))

    exclude_keys, exclude_reasons = _load_weekly_exclusions(root)

    all_rows = _read_jsonl(log_path)
    rows: List[Dict[str, Any]] = []
    excluded_audit: List[Dict[str, Any]] = []
    for row in all_rows:
        ts = _parse_utc(str(row.get("ts_utc", "")))
        if ts is None:
            continue
        if ts >= window_start:
            rk = _norm_ts_key(str(row.get("ts_utc", "")))
            if rk and exclude_keys and rk in exclude_keys:
                excluded_audit.append(
                    {
                        "ts_utc": str(row.get("ts_utc", "")),
                        "reason": exclude_reasons.get(rk, "listed in weekly readiness exclusions artifact"),
                    }
                )
                continue
            rows.append(row)

    total = len(rows)
    pass_count = sum(1 for r in rows if bool(r.get("overall_passed")) and int(r.get("exit_code", 1)) == 0)
    fail_count = total - pass_count
    pass_rate = round((pass_count / total) * 100.0, 2) if total else 0.0

    latest_ts = None
    if rows:
        latest_ts = max((_parse_utc(str(r.get("ts_utc", ""))) for r in rows), default=None)
    latest_ts_text = latest_ts.isoformat().replace("+00:00", "Z") if latest_ts else None

    payload = {
        "schema": "mkm_ai_v2_weekly_readiness_report_v1",
        "generated_at_utc": now.isoformat().replace("+00:00", "Z"),
        "window_days": max(args.window_days, 1),
        "window_start_utc": window_start.isoformat().replace("+00:00", "Z"),
        "window_end_utc": now.isoformat().replace("+00:00", "Z"),
        "log_path": str(log_path),
        "sample_count": total,
        "pass_count": pass_count,
        "fail_count": fail_count,
        "pass_rate_percent": pass_rate,
        "latest_run_utc": latest_ts_text,
        "excluded_from_stats": excluded_audit,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"weekly report written: {out_path}")
    print(f"pass_rate_percent={pass_rate} sample_count={total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
