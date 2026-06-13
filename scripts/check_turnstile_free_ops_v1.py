#!/usr/bin/env python3
"""Turnstile free-tier ops check (no Logpush — standard plan).

  py scripts/check_turnstile_free_ops_v1.py

Free path:
  - CF Turnstile widget (API probe)
  - no1kmedi siteverify + [turnstile-verify] stdout logs
  - CF dashboard Turnstile analytics (Human Chrome, optional)
"""
from __future__ import annotations

import json
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from mkm_cloudflare_token_v1 import _read_dotenv_key, _read_windows_user_env, token_fingerprint  # noqa: E402

ACCOUNT = "646e42cf881ab43043c32430e99d9af4"
OUT = ROOT / "docs" / "final" / "artifacts" / "turnstile_free_ops_check_v1_latest.json"
WIZARD_PROBE = ROOT / "reports" / "turnstile_logpush_wizard_probe_latest.json"
COMMANDER = ROOT / "docs" / "final" / "artifacts" / "turnstile_commander_ops_check_v1_latest.json"


def _tok() -> str:
    import os

    return (
        _read_windows_user_env("CLOUDFLARE_TURNSTILE_API_TOKEN")
        or os.environ.get("CLOUDFLARE_TURNSTILE_API_TOKEN", "").strip()
        or _read_dotenv_key("CLOUDFLARE_TURNSTILE_API_TOKEN")
    ).strip()


def _api(tok: str, path: str) -> tuple[int, dict]:
    req = urllib.request.Request(
        f"https://api.cloudflare.com/client/v4{path}",
        headers={"Authorization": f"Bearer {tok}", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {"success": False}


def main() -> int:
    doc: dict = {
        "schema": "turnstile_free_ops_check_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "track": "free_standard_plan",
        "logpush": "deferred_enterprise_or_workers_paid",
        "reproduce": "py scripts/check_turnstile_free_ops_v1.py",
        "free_path": {
            "widget_api": "py scripts/check_turnstile_commander_ops_v1.py",
            "app_verify_logs": "projects/no1kmedi/src/lib/turnstileServerV1.ts [turnstile-verify]",
            "dashboard_analytics": f"https://dash.cloudflare.com/{ACCOUNT}/turnstile",
            "env_sync": "py scripts/sync_turnstile_env_to_no1kmedi_v1.py --target all",
        },
    }

    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_turnstile_commander_ops_v1.py")],
        cwd=str(ROOT),
        check=False,
    )
    if COMMANDER.is_file():
        try:
            commander = json.loads(COMMANDER.read_text(encoding="utf-8"))
            doc["commander_decision"] = commander.get("decision")
            widgets = (
                (commander.get("api_probes") or [{}])[0]
                .get("probe", {})
                .get("widgets_redacted")
            )
            doc["widget_sitekey"] = (widgets[0] or {}).get("sitekey") if widgets else None
        except json.JSONDecodeError:
            doc["commander_decision"] = "artifact_parse_failed"

    if WIZARD_PROBE.is_file():
        try:
            wiz = json.loads(WIZARD_PROBE.read_text(encoding="utf-8"))
            doc["logpush_plan_gate"] = wiz.get("decision")
        except json.JSONDecodeError:
            pass

    tok = _tok()
    doc["turnstile_token_fingerprint"] = token_fingerprint(tok) if tok else None
    if tok:
        _, pl = _api(tok, f"/accounts/{ACCOUNT}/challenges/widgets")
        doc["widgets_api_ok"] = bool(pl.get("success"))
        result = pl.get("result") if isinstance(pl.get("result"), list) else []
        doc["widget_count"] = len(result)

    no1kmedi_env = ROOT / "projects" / "no1kmedi" / ".env.local"
    doc["no1kmedi_sitekey_configured"] = False
    if no1kmedi_env.is_file():
        for line in no1kmedi_env.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.strip().startswith("NEXT_PUBLIC_TURNSTILE_SITEKEY="):
                doc["no1kmedi_sitekey_configured"] = bool(line.split("=", 1)[1].strip())
                break

    widget_ok = doc.get("commander_decision") == "API_OK_WIDGETS_PRESENT" or doc.get("widgets_api_ok")
    if widget_ok and doc.get("no1kmedi_sitekey_configured"):
        doc["decision"] = "FREE_PATH_OK"
    elif widget_ok:
        doc["decision"] = "FREE_PATH_WIDGET_OK_SYNC_NO1KMEDI"
    else:
        doc["decision"] = "FREE_PATH_BLOCKED_WIDGET"

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    print(json.dumps(doc, indent=2, ensure_ascii=False))
    return 0 if doc["decision"].startswith("FREE_PATH_OK") or doc["decision"] == "FREE_PATH_WIDGET_OK_SYNC_NO1KMEDI" else 2


if __name__ == "__main__":
    raise SystemExit(main())
