#!/usr/bin/env python3
"""Purge mkmlife.com bloom slice + oracle-sphere cache (CF API, env token)."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MKMLIFE_ZONE_ID = "259a847ea3643566383972ebd3ede918"
DEFAULT_FILES = (
    "https://mkmlife.com/data/logos_cosmic_anchor_graph_bloom_slice_v1.json",
    "https://www.mkmlife.com/data/logos_cosmic_anchor_graph_bloom_slice_v1.json",
    "https://mkmlife.com/oracle-sphere",
    "https://www.mkmlife.com/oracle-sphere",
)
OUT = ROOT / "reports/cloudflare_mkmlife_bloom_cache_purge_v1_latest.json"


def _load_dotenv_token() -> None:
    dotenv = ROOT / ".env"
    if not dotenv.is_file():
        return
    for line in dotenv.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key in ("MKM_MKMLIFE_CF_DEPLOY_TOKEN", "CLOUDFLARE_API_TOKEN", "CF_API_TOKEN") and val:
            os.environ.setdefault("CLOUDFLARE_API_TOKEN", val)


def main() -> int:
    _load_dotenv_token()
    tok = (
        os.environ.get("MKM_MKMLIFE_CF_DEPLOY_TOKEN", "").strip()
        or os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()
        or os.environ.get("CF_API_TOKEN", "").strip()
    )
    if not tok:
        print("CLOUDFLARE_API_TOKEN missing", file=sys.stderr)
        return 1

    url = f"https://api.cloudflare.com/client/v4/zones/{MKMLIFE_ZONE_ID}/purge_cache"
    body = json.dumps({"files": list(DEFAULT_FILES)}).encode()
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"},
    )
    report: dict[str, object] = {
        "schema": "cloudflare_mkmlife_bloom_cache_purge_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "zone_id": MKMLIFE_ZONE_ID,
        "files": list(DEFAULT_FILES),
    }
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
        report["http"] = resp.status
        report["success"] = bool(data.get("success"))
        report["errors"] = data.get("errors") or []
    except urllib.error.HTTPError as e:
        report["http"] = e.code
        report["success"] = False
        try:
            report["errors"] = json.loads(e.read().decode())
        except Exception:
            report["errors"] = [str(e)]
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"FAIL: purge http={e.code}", file=sys.stderr)
        return 2

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {OUT}")
    print(f"  success={report['success']} files={len(DEFAULT_FILES)}")
    return 0 if report.get("success") else 2


if __name__ == "__main__":
    raise SystemExit(main())
