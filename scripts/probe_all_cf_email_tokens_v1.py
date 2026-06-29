#!/usr/bin/env python3
"""Probe all known Cloudflare token env keys for Email Routing API (no secrets printed)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from mkm_cloudflare_token_v1 import _read_dotenv_key, _read_windows_user_env  # noqa: E402

KEYS = (
    "MKM_NO1KMEDI_EMAIL_ROUTING_TOKEN",
    "CLOUDFLARE_API_TOKEN",
    "CF_API_TOKEN",
    "MKM_MKMLIFE_CF_ANALYTICS_TOKEN",
    "CLOUDFLARE_RULESETS_API_TOKEN",
    "MKM_CLOUDFLARE_RULESETS_TOKEN",
    "MKM_CLOUDFLARE_PERSONADIARY_DNS_TOKEN",
    "MKM_CLOUDFLARE_JEMA_AI_REDIRECT_TOKEN",
)
NO1K_ZONE = "1516522160411707c33f84e145416a53"
ACCOUNT = "646e42cf881ab43043c32430e99d9af4"


def _tok(key: str) -> tuple[str, str]:
    v = _read_windows_user_env(key)
    if v:
        return v.strip(), f"user:{key}"
    v = os.environ.get(key, "").strip()
    if v:
        return v, f"env:{key}"
    v = _read_dotenv_key(key)
    if v:
        return v.strip(), f".env:{key}"
    return "", ""


def _get(tok: str, path: str) -> tuple[int, dict]:
    req = urllib.request.Request(
        f"https://api.cloudflare.com/client/v4{path}",
        headers={"Authorization": f"Bearer {tok}", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {"success": False}


def main() -> int:
    seen: set[str] = set()
    winner: tuple[str, str] | None = None
    out = {"schema": "probe_all_cf_email_tokens_v1", "probes": []}
    for key in KEYS:
        tok, src = _tok(key)
        if not tok or tok in seen:
            continue
        seen.add(tok)
        _, v = _get(tok, "/user/tokens/verify")
        st_r, p_r = _get(tok, f"/zones/{NO1K_ZONE}/email/routing")
        st_a, p_a = _get(tok, f"/accounts/{ACCOUNT}/email/routing/addresses")
        st_rules, p_rules = _get(tok, f"/zones/{NO1K_ZONE}/email/routing/rules")
        row = {
            "key": key,
            "source": src,
            "verify_ok": v.get("success"),
            "routing_ok": p_r.get("success"),
            "routing_http": st_r,
            "addresses_ok": p_a.get("success"),
            "addresses_http": st_a,
            "rules_ok": p_rules.get("success"),
            "rules_http": st_rules,
        }
        if p_r.get("success") and p_r.get("result"):
            row["routing_enabled"] = p_r["result"].get("enabled")
            row["routing_status"] = p_r["result"].get("status")
        if p_a.get("success"):
            row["destinations"] = [
                {"email": a.get("email"), "verified": a.get("verified")}
                for a in (p_a.get("result") or [])
            ]
        if p_rules.get("success"):
            row["rules"] = []
            for rule in p_rules.get("result") or []:
                matchers = rule.get("matchers") or []
                actions = rule.get("actions") or []
                local = next(
                    (m.get("value") for m in matchers if m.get("type") == "literal"),
                    None,
                )
                dest = next(
                    (a.get("value") for a in actions if a.get("type") == "forward"),
                    None,
                )
                row["rules"].append(
                    {
                        "id": rule.get("id"),
                        "enabled": rule.get("enabled"),
                        "local": local,
                        "forward": dest,
                    }
                )
        out["probes"].append(row)
        if p_r.get("success") and not winner:
            winner = (key, src)
        print(json.dumps(row, ensure_ascii=False))

    report = ROOT / "reports" / "probe_all_cf_email_tokens_latest.json"
    report.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    if winner:
        print(f"WINNER_KEY={winner[0]} source={winner[1]}")
        return 0
    print("NO_TOKEN_WITH_EMAIL_ROUTING")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
