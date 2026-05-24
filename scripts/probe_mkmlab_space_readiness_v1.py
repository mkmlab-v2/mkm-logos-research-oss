#!/usr/bin/env python3
"""Probe mkmlab.space DNS + HTTP; write reports/mkmlab_space_readiness_latest.json."""

from __future__ import annotations

import json
import os
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "mkmlab_space_readiness_latest.json"
APEX = "mkmlab.space"
URLS = [
    f"https://{APEX}/",
    f"https://{APEX}/en.html",
    f"https://{APEX}/smartfarm-blueprint.html",
    f"https://{APEX}/shared/css/main.css?v=20260521-1",
    f"https://www.{APEX}/",
]
UA = "MKM-MkmlabSpace-Probe/1.0"


def resolve_a(host: str) -> list[str]:
    try:
        _, _, ips = socket.gethostbyname_ex(host)
        return sorted(ips)
    except socket.gaierror as exc:
        return [f"error:{exc}"]


def http_probe(url: str, timeout: int = 25) -> dict[str, Any]:
    req = Request(url, headers={"User-Agent": UA})
    try:
        with urlopen(req, timeout=timeout) as resp:
            body = resp.read(512).decode("utf-8", "ignore")
            hdrs = {k.lower(): v for k, v in resp.headers.items()}
            return {
                "url": url,
                "ok": 200 <= int(resp.status) < 400,
                "status": int(resp.status),
                "final_url": resp.geturl(),
                "body_snippet": body[:200],
                "server": hdrs.get("server", ""),
                "platform": hdrs.get("platform", ""),
                "panel": hdrs.get("panel", ""),
            }
    except HTTPError as exc:
        hdrs = {k.lower(): v for k, v in (exc.headers.items() if exc.headers else [])}
        return {
            "url": url,
            "ok": False,
            "status": int(exc.code),
            "final_url": url,
            "error": str(exc),
            "server": hdrs.get("server", ""),
            "platform": hdrs.get("platform", ""),
            "panel": hdrs.get("panel", ""),
        }
    except URLError as exc:
        return {
            "url": url,
            "ok": False,
            "status": None,
            "final_url": url,
            "error": str(exc.reason if hasattr(exc, "reason") else exc),
        }


def main() -> int:
    redesign = ROOT / "mkmlab-redesign"
    required = [
        redesign / "index.html",
        redesign / "en.html",
        redesign / "shared" / "css" / "main.css",
    ]
    local_ok = all(p.is_file() for p in required)
    probes = [http_probe(u) for u in URLS]
    http_ok = all(p.get("ok") for p in probes)
    zips = sorted((ROOT / "reports").glob("mkmlab-redesign_*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
    latest_zip = str(zips[0].relative_to(ROOT)).replace("\\", "/") if zips else None
    hcdn_403 = any(p.get("status") == 403 and p.get("server") == "hcdn" for p in probes)
    origin_ip = os.environ.get("MKMLAB_VPS_ORIGIN_IP", "148.230.97.246")
    origin_probe: dict[str, Any] = {"url": f"http://{origin_ip}/", "host": APEX}
    try:
        req = Request(
            f"http://{origin_ip}/",
            headers={"User-Agent": UA, "Host": APEX},
        )
        with urlopen(req, timeout=15) as resp:
            origin_probe.update(
                {
                    "ok": 200 <= int(resp.status) < 400,
                    "status": int(resp.status),
                    "server": resp.headers.get("Server", ""),
                }
            )
    except HTTPError as exc:
        origin_probe.update({"ok": False, "status": int(exc.code), "error": str(exc)})
    except URLError as exc:
        origin_probe.update({"ok": False, "status": None, "error": str(exc.reason if hasattr(exc, "reason") else exc)})

    payload = {
        "schema": "mkmlab_space_readiness_v1",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "apex": APEX,
        "local_redesign_ready": local_ok,
        "local_paths": [str(p.relative_to(ROOT)).replace("\\", "/") for p in required],
        "dns_a_apex": resolve_a(APEX),
        "dns_a_www": resolve_a(f"www.{APEX}"),
        "http_probes": probes,
        "http_all_ok": http_ok,
        "latest_deploy_zip": latest_zip,
        "hostinger_hcdn_403": hcdn_403,
        "deploy_hint": (
            "Hostinger VPS (MKM_VPS_HOST, default srv1101456) + Cloudflare DNS/proxy: "
            "powershell -File scripts/Sync-MkmlabRedesignToVps_v1.ps1 "
            "(remote MKMLAB_VPS_WEB_ROOT default /var/www/mkmlab; nginx vhost required). "
            "403+hcdn = apex still on Hostinger parking CDN, not VPS—fix CF A/AAAA to VPS IP."
        ),
        "channel_split": "mkmlab.space=research+products; jema-ai.com=commercial",
        "jema_ai_hub_link": "projects/no1kmedi/marketing-site/public-copy.json hub_links.research_mkmlab",
        "vps_origin_probe": origin_probe,
        "vps_origin_ip": origin_ip,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": local_ok, "http_all_ok": http_ok, "out": str(OUT)}, ensure_ascii=False))
    return 0 if local_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
