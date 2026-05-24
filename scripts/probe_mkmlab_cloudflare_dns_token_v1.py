#!/usr/bin/env python3
"""Diagnose mkmlab.space Cloudflare DNS 403 — token source, zone id match, read vs edit."""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "mkmlab_cloudflare_dns_token_probe_latest.json"
ZONE = "mkmlab.space"
ZID_EXPECTED = "38a47f29983bd4ebce3798be08f59ba3"


def _fp(s: str) -> str:
    s = s.strip()
    if len(s) < 12:
        return "(short)"
    return f"{s[:6]}...{s[-4:]}"


def _token_sources() -> list[dict]:
    rows: list[dict] = []
    for key in ("CLOUDFLARE_API_TOKEN", "CF_API_TOKEN"):
        v = os.environ.get(key, "").strip()
        if v:
            rows.append({"source": f"process_env:{key}", "len": len(v), "fp": _fp(v)})
    env = ROOT / ".env"
    if env.is_file():
        for line in env.read_text(encoding="utf-8", errors="ignore").splitlines():
            for key in ("CLOUDFLARE_API_TOKEN", "CF_API_TOKEN", "CLOUDFLARE_ZONE_ID"):
                if line.startswith(f"{key}="):
                    val = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if "TOKEN" in key:
                        rows.append({"source": f".env:{key}", "len": len(val), "fp": _fp(val)})
                    else:
                        rows.append({"source": f".env:{key}", "value": val})
    return rows


def _resolve_token() -> tuple[str, str]:
    sys.path.insert(0, str(ROOT / "scripts"))
    from mkm_cloudflare_token_v1 import resolve_cloudflare_token

    return resolve_cloudflare_token()


def _req(method: str, url: str, token: str, body: dict | None = None) -> dict:
    data = None
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            return {"http": resp.status, "json": json.loads(resp.read().decode("utf-8"))}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            j = json.loads(raw)
        except json.JSONDecodeError:
            j = {"raw": raw[:500]}
        return {"http": e.code, "json": j}


def main() -> int:
    token, used = _resolve_token()
    doc: dict = {
        "schema": "mkmlab_cloudflare_dns_token_probe_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "token_sources_seen": _token_sources(),
        "token_used_by_resolve_cloudflare_token": {"source": used, "fp": _fp(token) if token else None},
        "zone_expected": ZONE,
        "zone_id_used": ZID_EXPECTED,
        "checks": [],
    }
    if not token:
        doc["error"] = "no token"
        OUT.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"ok": False, "out": str(OUT)}, ensure_ascii=False))
        return 2

    base = "https://api.cloudflare.com/client/v4"
    for label, method, url, body in [
        ("token_verify", "GET", f"{base}/user/tokens/verify", None),
        ("zone_by_name", "GET", f"{base}/zones?name={ZONE}", None),
        ("zone_by_id", "GET", f"{base}/zones/{ZID_EXPECTED}", None),
        ("dns_list", "GET", f"{base}/zones/{ZID_EXPECTED}/dns_records?per_page=5", None),
        ("settings_ssl_get", "GET", f"{base}/zones/{ZID_EXPECTED}/settings/ssl", None),
        (
            "settings_ssl_patch_dry",
            "PATCH",
            f"{base}/zones/{ZID_EXPECTED}/settings/ssl",
            {"value": "full"},
        ),
    ]:
        r = _req(method, url, token, body)
        j = r.get("json") or {}
        row = {"check": label, "http": r["http"], "success": j.get("success")}
        if label == "zone_by_id" and j.get("result"):
            row["zone_name"] = j["result"].get("name")
            row["zone_status"] = j["result"].get("status")
        if label == "token_verify" and j.get("result"):
            pols = []
            for p in j["result"].get("policies") or []:
                pgs = [g.get("name") for g in (p.get("permission_groups") or []) if g.get("name")]
                pols.append({"effect": p.get("effect"), "permission_groups": pgs[:8]})
            row["policies_sample"] = pols
        if not j.get("success") and j.get("errors"):
            row["errors"] = j["errors"][:3]
        doc["checks"].append(row)

    # Dry-run style: list apex A only (no mutation)
    r = _req("GET", f"{base}/zones/{ZID_EXPECTED}/dns_records?type=A&name={ZONE}", token)
    doc["apex_a_list"] = {"http": r["http"], "success": (r.get("json") or {}).get("success")}
    if (r.get("json") or {}).get("result"):
        doc["apex_a_list"]["records"] = [
            {"id": x.get("id"), "content": x.get("content"), "proxied": x.get("proxied")}
            for x in (r["json"]["result"])[:5]
        ]

    doc["diagnosis"] = []
    zid_check = next((c for c in doc["checks"] if c["check"] == "zone_by_id"), {})
    if zid_check.get("zone_name") and zid_check["zone_name"] != ZONE:
        doc["diagnosis"].append(
            f"WRONG_ZONE_ID: {ZID_EXPECTED} is {zid_check['zone_name']}, not {ZONE} — causes cross-zone 403"
        )
    dns_list = next((c for c in doc["checks"] if c["check"] == "dns_list"), {})
    if dns_list.get("http") == 403:
        doc["diagnosis"].append(
            "DNS_READ_403: token cannot read DNS on this zone_id (wrong id or zone not in token scope)"
        )
    elif dns_list.get("http") == 200:
        doc["diagnosis"].append("DNS_READ_OK: token can list records; PATCH needs Zone.DNS Edit")
    ssl_get = next((c for c in doc["checks"] if c["check"] == "settings_ssl_get"), {})
    ssl_patch = next((c for c in doc["checks"] if c["check"] == "settings_ssl_patch_dry"), {})
    if ssl_get.get("http") == 200:
        doc["diagnosis"].append("ZONE_SETTINGS_READ_OK")
    elif ssl_get.get("http") == 403:
        doc["diagnosis"].append(
            "ZONE_SETTINGS_READ_403: add permissionGroupKeys zone_settings+edit "
            "(scripts/Open-MkmlabCloudflareTokenTemplate_v1.ps1 URL) then update CLOUDFLARE_API_TOKEN"
        )
    if ssl_patch.get("success"):
        doc["diagnosis"].append("ZONE_SETTINGS_PATCH_OK: finalize_mkmlab_cloudflare_zone_v1.py should pass")
    elif ssl_patch.get("http") == 403:
        doc["diagnosis"].append("ZONE_SETTINGS_PATCH_403: Zone Settings Edit missing on token")
    tok_verify = next((c for c in doc["checks"] if c["check"] == "token_verify"), {})
    if dns_list.get("http") == 403 and tok_verify.get("http") == 200:
        doc["diagnosis"].append(
            "ROOT_CAUSE: token is valid but Zone.DNS Read/Edit missing on mkmlab.space "
            "(Zone Read / Tunnel token). Not wrong zone_id. Fix token in Cloudflare dashboard."
        )
    zbn = next((c for c in doc["checks"] if c["check"] == "zone_by_name"), {})
    if zbn.get("http") == 200 and not zbn.get("success"):
        doc["diagnosis"].append("zones?name= empty but zone_by_id may work — token scoped to zone id list only")

    sources = doc["token_sources_seen"]
    proc = [s for s in sources if s["source"].startswith("process_env")]
    dot = [s for s in sources if s["source"].startswith(".env")]
    used_fp = (doc.get("token_used_by_resolve_cloudflare_token") or {}).get("fp")
    if proc and dot and proc[0].get("fp") != dot[0].get("fp"):
        if used_fp and used_fp == dot[0].get("fp"):
            doc["diagnosis"].append(
                "CURSOR_STALE_PROCESS_TOKEN: Process env has a different token than User/.env; "
                "ensure script now prefers User (fixed). Clear Process CLOUDFLARE_* in Cursor if confused."
            )
        elif used_fp and used_fp == proc[0].get("fp"):
            doc["diagnosis"].append(
                "BUG: still using Process token — should prefer User; check mkm_cloudflare_token_v1.py"
            )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(OUT), "diagnosis": doc["diagnosis"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
