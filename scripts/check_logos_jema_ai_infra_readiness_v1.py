#!/usr/bin/env python3
"""Readiness gate: logos.jema-ai.com DNS + HTTPS + demo spine markers."""
from __future__ import annotations

import argparse
import json
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/logos_jema_ai_infra_readiness_latest.json"
URL = "https://logos.jema-ai.com/logos-research"
MARKERS = (
    "logos-research-page",
    "Scripture Research Workspace",
    "api.jemaai.cloud/public_showroom_logos_job_reading_pack_v1.html",
    "api.jemaai.cloud/public_showroom_meaning_topology_qa_v2.html",
    "Job Reading Pack",
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def dns_resolves(host: str) -> bool:
    try:
        socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        return True
    except socket.gaierror:
        return False


def http_get(url: str, timeout: float = 45.0) -> tuple[int, str]:
    req = Request(url, headers={"User-Agent": "mkm-logos-infra-readiness/1"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except URLError as e:
        if hasattr(e, "code") and e.code:
            return int(e.code), ""
        return 0, ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=URL)
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()

    host = "logos.jema-ai.com"
    dns_ok = dns_resolves(host)
    code, html = (0, "")
    if dns_ok:
        code, html = http_get(args.url)

    missing = [m for m in MARKERS if m not in html]
    ok = dns_ok and code == 200 and not missing

    doc = {
        "schema": "logos_jema_ai_infra_readiness_v1",
        "generated_at_utc": _utc(),
        "url": args.url,
        "dns_resolves": dns_ok,
        "http_code": code,
        "markers_missing": missing,
        "ok": ok,
        "blocked_on": None if ok else ("dns_nxdomain" if not dns_ok else "http_or_markers"),
        "next_if_dns_blocked": "scripts/Open-JemaAiLogosDnsTemplate_v1.ps1",
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "out": str(out), "dns_resolves": dns_ok, "http_code": code}))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
