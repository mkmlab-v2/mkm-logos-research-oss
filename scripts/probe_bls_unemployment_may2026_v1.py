#!/usr/bin/env python3
"""Probe BLS/FRED headline unemployment for May 2026 vs general_prophecy threshold 4.3%.

Does not mutate the registry. Use with Invoke-GeneralProphecyBlsUnrateResolve_v1.ps1 after human
confirms the suggested outcome matches the official BLS release.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import parse, request

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/bls_unemployment_probe_v1_latest.json"
THRESHOLD = 4.3
MAY_2026_OBS_DATE = "2026-05-01"
QID = "seed.macro.us_bls_unrate_gt_43_20260606"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fred_latest_unrate(api_key: str) -> list[dict[str, str]]:
    q = parse.urlencode(
        {
            "series_id": "UNRATE",
            "api_key": api_key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": 6,
        }
    )
    url = f"https://api.stlouisfed.org/fred/series/observations?{q}"
    req = request.Request(url=url, method="GET")
    with request.urlopen(req, timeout=20) as resp:
        doc = json.loads(resp.read().decode("utf-8"))
    rows: list[dict[str, str]] = []
    for row in doc.get("observations") or []:
        if not isinstance(row, dict):
            continue
        d = str(row.get("date") or "")
        v = str(row.get("value") or "").strip()
        if v and v != ".":
            rows.append({"date": d, "value": v})
    return rows


def probe(*, fred_key: str) -> dict[str, Any]:
    out: dict[str, Any] = {
        "schema": "bls_unemployment_probe_v1",
        "generated_at_utc": _utc(),
        "question_id": QID,
        "threshold_pct_strict_gt": THRESHOLD,
        "reference_month": "2026-05",
        "hypothesis_tier": "B",
        "research_only": True,
        "official_release_url": "https://www.bls.gov/news.release/empsit.nr0.htm",
    }
    if not fred_key:
        out.update(
            {
                "status": "not_ready",
                "reason": "FRED_API_KEY missing; confirm BLS table A-15 manually before resolve.",
                "suggested_outcome": None,
                "may_2026_release_ready": False,
            }
        )
        return out

    try:
        obs = _fred_latest_unrate(fred_key)
    except Exception as e:
        out.update(
            {
                "status": "error",
                "reason": str(e),
                "suggested_outcome": None,
                "may_2026_release_ready": False,
            }
        )
        return out

    out["fred_unrate_recent"] = obs
    may_row = next((r for r in obs if r.get("date") == MAY_2026_OBS_DATE), None)
    if may_row is None:
        latest = obs[0] if obs else {}
        out.update(
            {
                "status": "not_ready",
                "reason": f"FRED UNRATE has no {MAY_2026_OBS_DATE} row yet; latest={latest.get('date')}",
                "suggested_outcome": None,
                "may_2026_release_ready": False,
            }
        )
        return out

    rate = float(may_row["value"])
    suggested = "true" if rate > THRESHOLD else "false"
    out.update(
        {
            "status": "ok",
            "may_2026_sa_unemployment_pct": rate,
            "suggested_outcome": suggested,
            "may_2026_release_ready": True,
            "reason": f"FRED UNRATE {MAY_2026_OBS_DATE}={rate}% vs threshold strictly > {THRESHOLD}%",
            "human_confirm_required": True,
        }
    )
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--stdout-only", action="store_true")
    ns = ap.parse_args()
    doc = probe(fred_key=os.environ.get("FRED_API_KEY", "").strip())
    text = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    if ns.stdout_only:
        sys.stdout.write(text)
        return 0 if doc.get("status") == "ok" else 1
    ns.out_json.parent.mkdir(parents=True, exist_ok=True)
    ns.out_json.write_text(text, encoding="utf-8")
    sched_path = ROOT / "reports/bls_unemployment_watch_schedule_v1_latest.json"
    sched = {
        "schema": "bls_unemployment_watch_schedule_v1",
        "updated_at_utc": _utc(),
        "question_id": QID,
        "last_probe_status": doc.get("status"),
        "may_2026_release_ready": doc.get("may_2026_release_ready"),
        "release_window_local_date": "2026-06-06",
        "next_action": (
            "resolve"
            if doc.get("may_2026_release_ready")
            else "reprobe_on_or_after_release_window"
        ),
        "reprobe_command": "py scripts/probe_bls_unemployment_may2026_v1.py",
        "resolve_template": (
            "powershell -NoProfile -ExecutionPolicy Bypass -File "
            "scripts/Invoke-GeneralProphecyBlsUnrateResolve_v1.ps1 -Outcome <true|false>"
        ),
        "probe_pointer": str(ns.out_json.relative_to(ROOT)).replace("\\", "/"),
    }
    sched_path.write_text(
        json.dumps(sched, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "ok": doc.get("status") == "ok",
                "status": doc.get("status"),
                "out": str(ns.out_json),
                "schedule": str(sched_path),
            },
            ensure_ascii=False,
        )
    )
    return 0 if doc.get("may_2026_release_ready") else 1


if __name__ == "__main__":
    raise SystemExit(main())
