"""Set mkmlab.space registrar nameservers to Cloudflare via Hostinger API."""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "hostinger_mkmlab_nameservers_latest.json"
API_BASE = "https://developers.hostinger.com"
DOMAIN = "mkmlab.space"
DEFAULT_NS = ("sarah.ns.cloudflare.com", "sullivan.ns.cloudflare.com")


def _load_token() -> str | None:
    tok = os.environ.get("HOSTINGER_API_TOKEN") or os.environ.get("API_TOKEN")
    if tok:
        return tok.strip()
    dot = ROOT / ".env"
    if not dot.is_file():
        return None
    for line in dot.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        if k.strip() == "HOSTINGER_API_TOKEN":
            return v.strip().strip('"').strip("'")
    return None


def _api(method: str, path: str, token: str, body: dict | None = None) -> tuple[int, object]:
    url = f"{API_BASE}{path}"
    data = None
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "User-Agent": "hostinger-api-mcp/2.0 (MKM-automation)",
    }
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return resp.status, json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw) if raw.strip() else {"message": raw}
        except json.JSONDecodeError:
            payload = {"message": raw}
        return e.code, payload


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", default=DOMAIN)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--ns", nargs="+", default=list(DEFAULT_NS))
    args = ap.parse_args()

    token = _load_token()
    report: dict = {
        "schema": "hostinger_mkmlab_nameservers_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "domain": args.domain,
        "target_nameservers": list(args.ns),
        "token_present": bool(token),
        "ok": False,
    }

    if not token:
        report["error"] = "HOSTINGER_API_TOKEN missing"
        OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps({"ok": False, "out": str(OUT), "error": report["error"]}))
        return 2

    path = f"/api/domains/v1/portfolio/{args.domain}"
    st_get, detail = _api("GET", path, token)
    report["get_http"] = st_get
    report["get_ok"] = 200 <= st_get < 300
    if isinstance(detail, dict):
        ns_before = detail.get("name_servers") or detail.get("nameservers")
        if ns_before is not None:
            report["nameservers_before"] = ns_before

    if args.dry_run:
        report["ok"] = report.get("get_ok", False)
        report["action"] = "dry_run"
        OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps({"ok": report["ok"], "out": str(OUT), "dry_run": True}))
        return 0 if report["ok"] else 1

    if len(args.ns) < 2:
        report["error"] = "need at least two nameservers"
        OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps({"ok": False, "out": str(OUT), "error": report["error"]}))
        return 2

    body = {"ns1": args.ns[0], "ns2": args.ns[1]}
    st_put, put_resp = _api("PUT", f"{path}/nameservers", token, body)
    report["put_http"] = st_put
    report["put_ok"] = 200 <= st_put < 300
    report["put_body_shape"] = "ns1_ns2"
    if not report["put_ok"]:
        report["put_error"] = put_resp

    report["ok"] = bool(report.get("put_ok"))
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"ok": report["ok"], "out": str(OUT)}))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
