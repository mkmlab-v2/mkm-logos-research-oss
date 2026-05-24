#!/usr/bin/env python3
"""Apply zone-level 301 redirect (all paths) via Cloudflare dynamic redirect ruleset.

Example (jema12 → jema-ai.com):
  py scripts/setup_cloudflare_apex_redirect_v1.py --apex jema12.com --target-host jema-ai.com

Requires API token with Zone Rulesets Edit + Zone Read for the apex zone.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _load_dotenv_token() -> None:
    root = Path(__file__).resolve().parents[1]
    dotenv = root / ".env"
    if not dotenv.is_file():
        return
    for line in dotenv.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip().strip('"').strip("'")
        if key in ("CLOUDFLARE_API_TOKEN", "CF_API_TOKEN") and val:
            os.environ.setdefault("CLOUDFLARE_API_TOKEN", val)
            break


def _api(
    tok: str,
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
) -> tuple[int, dict[str, Any]]:
    url = f"https://api.cloudflare.com/client/v4{path}"
    data = None
    headers = {"Authorization": f"Bearer {tok}", "Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            payload = json.loads(e.read().decode("utf-8"))
        except Exception:
            payload = {"success": False, "errors": [{"message": str(e)}]}
        return e.code, payload


def _zone_lookup(tok: str, apex: str) -> dict[str, Any] | None:
    enc = urllib.parse.quote(apex, safe="")
    _, payload = _api(tok, "GET", f"/zones?name={enc}&status=active")
    if not payload.get("success"):
        return None
    for z in payload.get("result") or []:
        if (z.get("name") or "").lower() == apex.lower():
            return z
    return None


def _write_report(path: str, data: dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Wrote {path}")


def main() -> int:
    _load_dotenv_token()
    ap = argparse.ArgumentParser(description="Cloudflare apex 301 redirect (preserve path + query).")
    ap.add_argument("--apex", required=True, help="Source zone apex, e.g. jema12.com")
    ap.add_argument("--target-host", default="jema-ai.com", help="Target host without scheme")
    ap.add_argument("--zone-id", default="", help="Zone id when list zones is scoped away")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--out-json",
        default=os.path.join(
            os.environ.get("MKM_WORKSPACE_ROOT", r"C:\workspace"),
            "reports",
            "cloudflare_apex_redirect_setup_latest.json",
        ),
    )
    args = ap.parse_args()

    tok = (
        os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()
        or os.environ.get("CF_API_TOKEN", "").strip()
    )
    if not tok:
        print("CLOUDFLARE_API_TOKEN missing", file=sys.stderr)
        return 1

    apex = args.apex.strip().lower()
    target_host = args.target_host.strip().lower().rstrip("/")
    target_base = f"https://{target_host}"

    out: dict[str, Any] = {
        "schema": "cloudflare_apex_redirect_setup_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "apex": apex,
        "target_host": target_host,
        "dry_run": args.dry_run,
        "steps": [],
    }

    zone: dict[str, Any] | None = None
    if args.zone_id.strip():
        zid = args.zone_id.strip()
        _, pl = _api(tok, "GET", f"/zones/{zid}")
        if pl.get("success") and pl.get("result"):
            zone = pl["result"]
        out["steps"].append({"step": "zone_by_id", "ok": zone is not None, "zone_id": zid})
    else:
        zone = _zone_lookup(tok, apex)
        out["steps"].append(
            {
                "step": "zone_lookup",
                "ok": zone is not None,
                "zone_id": zone.get("id") if zone else None,
            }
        )

    if not zone:
        out["blocked"] = "zone_not_visible"
        out["manual"] = [
            f"Cloudflare 대시보드 → Websites에 {apex} 가 있는지 확인(Registrar 이전 ≠ zone 자동 생성일 수 있음).",
            "없으면: Websites → Add site → {apex} → active 후 NS 적용.",
            f"zone_id 확인 후: py scripts/setup_cloudflare_apex_redirect_v1.py --apex {apex} --zone-id <id>",
            "API 토큰에 Zone Rulesets Edit + 해당 zone Read 포함 필요.",
            f"수동: Rules → Redirect Rules → Single redirect → {apex}/* → {target_base}/$1 (301).",
        ]
        _write_report(args.out_json, out)
        print(f"BLOCKED: zone {apex} not visible to API token")
        for line in out["manual"]:
            print(f"  - {line}")
        return 2

    zid = zone["id"]
    out["zone_id"] = zid

    rule_body = {
        "rules": [
            {
                "action": "redirect",
                "expression": "true",
                "description": f"{apex} → {target_host} (301, preserve path)",
                "action_parameters": {
                    "from_value": {
                        "status_code": 301,
                        "target_url": {
                            "expression": (
                                f'concat("{target_base}", http.request.uri.path)'
                            ),
                        },
                        "preserve_query_string": True,
                    }
                },
            }
        ]
    }

    if args.dry_run:
        out["action"] = "dry_run_only"
        out["ruleset_body"] = rule_body
        _write_report(args.out_json, out)
        print(f"DRY-RUN ok zone_id={zid} {apex} -> {target_base}<path>")
        return 0

    path = f"/zones/{zid}/rulesets/phases/http_request_dynamic_redirect/entrypoint"
    st, pl = _api(tok, "PUT", path, rule_body)
    out["steps"].append(
        {
            "step": "redirect_entrypoint_put",
            "http": st,
            "success": pl.get("success"),
            "errors": pl.get("errors"),
            "result_id": (pl.get("result") or {}).get("id"),
        }
    )
    if not pl.get("success"):
        _write_report(args.out_json, out)
        print("redirect ruleset PUT failed", pl.get("errors"), file=sys.stderr)
        return 3

    out["action"] = "redirect_applied"
    _write_report(args.out_json, out)
    print(f"OK: {apex} -> {target_base} (301, all paths)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
