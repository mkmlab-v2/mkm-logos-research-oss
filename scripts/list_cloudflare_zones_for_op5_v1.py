#!/usr/bin/env python3
"""List CF zones visible to token; optional apply jema12 studio redirect."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from mkm_cloudflare_token_v1 import resolve_cloudflare_token  # noqa: E402


def _load_token() -> str:
    tok, _ = resolve_cloudflare_token()
    return tok


def main() -> int:
    tok = _load_token()
    if not tok:
        print("no token", file=sys.stderr)
        return 1
    import urllib.parse
    import urllib.request

    names = []
    page = 1
    while True:
        url = f"https://api.cloudflare.com/client/v4/zones?per_page=50&page={page}"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {tok}"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            pl = json.loads(resp.read())
        if not pl.get("success"):
            print(json.dumps(pl, ensure_ascii=False, indent=2))
            return 2
        for z in pl.get("result") or []:
            names.append((z.get("name"), z.get("id")))
        total_pages = (pl.get("result_info") or {}).get("total_pages", 1)
        if page >= total_pages:
            break
        page += 1
    out_path = ROOT / "reports" / "cloudflare_op5_zone_inventory_v1.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc = {
        "schema": "cloudflare_op5_zone_inventory_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "registry_ssot": "docs/final/artifacts/mkm_cloudflare_zone_registry_v1.json",
        "zones": names,
    }
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(doc, ensure_ascii=False, indent=2))
    jema12 = next((zid for n, zid in names if n == "jema12.com"), None)
    if not jema12:
        return 0
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts/setup_cloudflare_jema12_studio_oracle_redirect_v1.py"), "--zone-id", jema12],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    doc["jema12_studio_apply"] = {"exit_code": r.returncode, "stdout_tail": (r.stdout or "")[-400:]}
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
