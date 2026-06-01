#!/usr/bin/env python3
"""Public DNS/HTTPS smoke for no1kmedi clinic/research/api hosts (no CF API token)."""
from __future__ import annotations

import json
import socket
import ssl
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "no1kmedi_public_dns_verify_latest.json"
ORIGIN_IP = "148.230.97.246"
HOSTS = [
    {"host": "research.no1kmedi.com", "https": True},
    {"host": "clinic.no1kmedi.com", "https": True},
    {"host": "www.clinic.no1kmedi.com", "https": True},
    {"host": "no1kmedi.com", "https": True},
    {"host": "api.no1kmedi.com", "https": True, "expect_json_ok": True},
]


def _resolve_a(host: str) -> list[str]:
    try:
        infos = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except socket.gaierror:
        return []
    ips: list[str] = []
    for info in infos:
        ip = info[4][0]
        if ip and ip not in ips:
            ips.append(ip)
    return ips


def _https_probe(host: str, expect_json_ok: bool) -> dict:
    url = f"https://{host}/"
    if expect_json_ok:
        url = f"https://{host}/health"
    row: dict = {"url": url, "ok": False}
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "mkm-no1kmedi-dns-verify/1"})
        with urllib.request.urlopen(req, timeout=25) as resp:
            row["status"] = resp.status
            body = resp.read(8000).decode("utf-8", errors="replace")
            if expect_json_ok:
                row["ok"] = '"ok"' in body and "true" in body
            else:
                row["ok"] = 200 <= int(resp.status) < 400
    except urllib.error.HTTPError as e:
        row["status"] = e.code
        row["ok"] = 200 <= e.code < 400 and not expect_json_ok
    except (urllib.error.URLError, ssl.SSLError, TimeoutError) as e:
        row["error"] = str(e)[:200]
    return row


def main() -> int:
    rows = []
    for spec in HOSTS:
        host = spec["host"]
        ips = _resolve_a(host)
        cf_proxied = any(not ip.startswith(ORIGIN_IP) for ip in ips) if ips else False
        direct_origin = ORIGIN_IP in ips
        row = {
            "host": host,
            "resolved_ips": ips,
            "cf_proxied_likely": cf_proxied,
            "direct_origin_ip": direct_origin,
            "dns_ok": bool(ips),
        }
        if spec.get("https"):
            row["https"] = _https_probe(host, bool(spec.get("expect_json_ok")))
            row["all_ok"] = row["dns_ok"] and row["https"].get("ok")
        else:
            row["all_ok"] = row["dns_ok"]
        rows.append(row)

    out = {
        "schema": "no1kmedi_public_dns_verify_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "origin_ip": ORIGIN_IP,
        "hosts": rows,
        "all_ok": all(r.get("all_ok") for r in rows),
    }
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))
    return 0 if out["all_ok"] else 4


if __name__ == "__main__":
    raise SystemExit(main())
