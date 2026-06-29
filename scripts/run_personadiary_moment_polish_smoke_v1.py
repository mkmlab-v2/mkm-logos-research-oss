#!/usr/bin/env python3
"""Smoke PersonaDiary moment API + runtime polish chain [HYPO]."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "personadiary_moment_polish_smoke_latest.json"
DEFAULT_BASE = "http://127.0.0.1:3010"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _post_moment(base: str, *, timeout_sec: int = 90) -> dict:
    url = f"{base.rstrip('/')}/api/personadiary/moment"
    body = json.dumps({"text": "오늘 점심 뭐 먹을까?", "profile_id": "commander"}, ensure_ascii=False).encode(
        "utf-8"
    )
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    base = (os.getenv("NO1KMEDI_DEV_URL") or DEFAULT_BASE).strip()
    runtime_flag = (os.getenv("MKM_PERSONADIARY_MOMENT_RUNTIME_POLISH") or "auto").strip()

    smoke: dict = {
        "schema": "personadiary_moment_polish_smoke_v1",
        "generated_at_utc": _utc(),
        "base_url": base,
        "runtime_polish_flag": runtime_flag,
        "lane": "research_only",
        "hypothesis_tier": "B",
        "ok": False,
    }

    try:
        payload = _post_moment(base)
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        smoke["error"] = str(exc)[:300]
        smoke["hint"] = "Start: cd projects/no1kmedi; npm run dev (port 3010)"
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(smoke, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(smoke, ensure_ascii=False, indent=2))
        return 1

    moment = payload.get("moment") or {}
    polish_meta = moment.get("polish_meta") or {}
    smoke["moment"] = {
        "ok": payload.get("ok") is True,
        "intent": moment.get("intent"),
        "summary_ko_len": len(str(moment.get("summary_ko") or "")),
        "summary_ko_polished": moment.get("summary_ko_polished"),
        "polish_meta": polish_meta,
    }
    smoke["ok"] = (
        payload.get("ok") is True
        and moment.get("intent") == "meal"
        and bool(moment.get("summary_ko"))
    )
    # Polish is optional in smoke — pass if deterministic works; note polish separately
    smoke["polish_ok"] = bool(moment.get("summary_ko_polished")) and polish_meta.get("applied") is True
    smoke["polish_backend"] = polish_meta.get("backend")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(smoke, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(smoke, ensure_ascii=False, indent=2))
    return 0 if smoke["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
