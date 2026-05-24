#!/usr/bin/env python3
"""Probe whether current CLOUDFLARE_API_TOKEN can read/write dynamic redirect rulesets."""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ZONE_ID = "a9f34634593eef57609e48c3ffbe6f24"


def _load_token() -> str:
    dotenv = ROOT / ".env"
    if dotenv.is_file():
        for line in dotenv.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key, val = key.strip(), val.strip().strip('"').strip("'")
            if key in ("CLOUDFLARE_API_TOKEN", "CF_API_TOKEN", "CLOUDFLARE_RULESETS_API_TOKEN") and val:
                os.environ.setdefault(key, val)
    return (
        os.environ.get("CLOUDFLARE_RULESETS_API_TOKEN", "").strip()
        or os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()
        or os.environ.get("CF_API_TOKEN", "").strip()
    )


def _api(tok: str, method: str, path: str) -> tuple[int, dict]:
    req = urllib.request.Request(
        f"https://api.cloudflare.com/client/v4{path}",
        method=method,
        headers={"Authorization": f"Bearer {tok}", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            payload = json.loads(e.read().decode("utf-8"))
        except Exception:
            payload = {"success": False, "errors": [{"message": str(e)}]}
        return e.code, payload


def main() -> int:
    tok = _load_token()
    if not tok:
        print("CLOUDFLARE_API_TOKEN missing", file=sys.stderr)
        return 1

    out: dict = {"schema": "cloudflare_rulesets_permission_probe_v1", "checks": []}

    for label, q in [
        ("rulesets_edit", "Zone Rulesets"),
        ("zone_read", "Zone"),
    ]:
        enc = urllib.parse.urlencode({"name": q})
        st, pl = _api(tok, "GET", f"/user/tokens/permission_groups?{enc}")
        groups = pl.get("result") or []
        out["checks"].append(
            {
                "query": q,
                "http": st,
                "success": pl.get("success"),
                "groups": [{"id": g.get("id"), "name": g.get("name")} for g in groups[:12]],
            }
        )

    ep = f"/zones/{ZONE_ID}/rulesets/phases/http_request_dynamic_redirect/entrypoint"
    st, pl = _api(tok, "GET", ep)
    out["entrypoint_get"] = {
        "http": st,
        "success": pl.get("success"),
        "rule_count": len((pl.get("result") or {}).get("rules") or []) if pl.get("success") else 0,
        "errors": pl.get("errors"),
    }

    path = ROOT / "reports" / "cloudflare_rulesets_permission_probe_latest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))
    ok = out["entrypoint_get"].get("success") is True
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
