#!/usr/bin/env python3
"""Open-beta traffic observability: aggregate magic-orb live probe history (availability time series)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HISTORY = ROOT / "reports" / "magic_orb_live_probe_history.jsonl"
LATEST_PROBE = ROOT / "reports" / "magic_orb_live_probe_latest.json"
CF_PROBE = ROOT / "reports" / "mkmlife_cf_traffic_probe_latest.json"
DEFAULT_OUT = ROOT / "reports" / "magic_orb_open_beta_traffic_summary_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_ts(raw: str) -> datetime | None:
    try:
        return datetime.strptime(raw, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _load_history(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def _window_stats(rows: list[dict], days: int) -> dict:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    in_window = []
    for row in rows:
        ts = _parse_ts(str(row.get("checked_at_utc") or ""))
        if ts and ts >= cutoff:
            in_window.append(row)
    ok_count = sum(1 for r in in_window if r.get("all_ok"))
    total = len(in_window)
    rate = (ok_count / total) if total else None
    return {
        "days": days,
        "runs": total,
        "all_ok_runs": ok_count,
        "all_ok_rate": round(rate, 4) if rate is not None else None,
    }


def _url_rollups(rows: list[dict]) -> dict[str, dict]:
    by_id: dict[str, dict] = {}
    for row in rows:
        for item in row.get("results") or []:
            if not isinstance(item, dict):
                continue
            rid = str(item.get("id") or "")
            if not rid:
                continue
            slot = by_id.setdefault(
                rid,
                {
                    "checks": 0,
                    "ok_checks": 0,
                    "last_status": None,
                    "last_ok": None,
                    "last_checked_at_utc": None,
                },
            )
            slot["checks"] += 1
            if item.get("ok"):
                slot["ok_checks"] += 1
            slot["last_status"] = item.get("status")
            slot["last_ok"] = item.get("ok")
            slot["last_checked_at_utc"] = row.get("checked_at_utc")
    for slot in by_id.values():
        checks = int(slot["checks"])
        slot["availability_rate"] = round(slot["ok_checks"] / checks, 4) if checks else None
    return by_id


def main() -> int:
    ap = argparse.ArgumentParser(description="Build magic-orb open-beta traffic/availability summary from probe history.")
    ap.add_argument("--history-jsonl", type=Path, default=HISTORY)
    ap.add_argument("--latest-probe-json", type=Path, default=LATEST_PROBE)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    history_path = args.history_jsonl if args.history_jsonl.is_absolute() else ROOT / args.history_jsonl
    latest_path = args.latest_probe_json if args.latest_probe_json.is_absolute() else ROOT / args.latest_probe_json
    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json

    rows = _load_history(history_path)
    latest_probe = None
    if latest_path.is_file():
        latest_probe = json.loads(latest_path.read_text(encoding="utf-8"))

    cf_probe = None
    if CF_PROBE.is_file():
        cf_probe = json.loads(CF_PROBE.read_text(encoding="utf-8"))

    streak_all_ok = 0
    for row in reversed(rows):
        if row.get("all_ok"):
            streak_all_ok += 1
        else:
            break

    try:
        history_rel = str(history_path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        history_rel = str(history_path)

    doc = {
        "schema": "magic_orb_open_beta_traffic_summary_v1",
        "generated_at_utc": _utc_now(),
        "open_beta_phase": True,
        "payment_e2e_deferred": True,
        "history_path": history_rel,
        "history_entries_total": len(rows),
        "streak_all_ok_from_latest": streak_all_ok,
        "windows": {
            "last_24h": _window_stats(rows, 1),
            "last_7d": _window_stats(rows, 7),
            "last_30d": _window_stats(rows, 30),
        },
        "urls": _url_rollups(rows),
        "latest_probe": latest_probe,
        "cf_zone_probe": cf_probe,
        "observability_note_ko": (
            "본 리포트는 live probe 가용성·마커 시계열입니다. "
            "실제 UV·세션·지역 분포는 Cloudflare Analytics(mkmlife.com)에서 별도 확인합니다. "
            "결제·PayApp E2E는 오픈베타 후순위입니다."
        ),
        "track_wall": {
            "hypothesis_tier": "B",
            "non_gating": True,
            "no_track_a_live_merge": True,
        },
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
