#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ensure mutda.ai DNS + Workers routes for mutda-news-open-beta OPEN_BETA.

Requires API token with Zone DNS Edit + Workers Routes Edit on zone mutda.ai.
Current default CLOUDFLARE_API_TOKEN often lacks these (403 code 10000) → Tier3 Human.

  py scripts/ensure_mutda_ai_open_beta_route_dns_v1.py --dry-run
  py scripts/ensure_mutda_ai_open_beta_route_dns_v1.py --apply
  py scripts/ensure_mutda_ai_open_beta_route_dns_v1.py --smoke-only

Does NOT claim PRODUCT_DONE / PUBLIC_LIVE without smoke PASS.
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from mkm_cloudflare_token_v1 import resolve_cloudflare_token  # noqa: E402

ACCOUNT = "646e42cf881ab43043c32430e99d9af4"
ZONE_ID = "924aa7f2ccd669c07967c67f89ee1a1a"
ZONE = "mutda.ai"
SCRIPT = "mutda-news-open-beta"
OUT = ROOT / "docs/final/artifacts/mudda_mutda_news_open_beta_route_dns_ensure_v0_1_latest.json"
STATUS = ROOT / "docs/final/artifacts/mudda_mutda_news_open_beta_status_v0_1_latest.json"

# Proxied apex placeholder used with Workers routes (CF workers convention)
AAAA_PLACEHOLDER = "100::"

TOKEN_EXTRA = (
    "MKM_CLOUDFLARE_MUTDA_DNS_ROUTES_TOKEN",
    "MKM_CLOUDFLARE_MUTDA_ZONE_TOKEN",
)


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _api(tok: str, method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
    headers = {"Authorization": f"Bearer {tok}", "Accept": "application/json"}
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(
        f"https://api.cloudflare.com/client/v4{path}",
        data=data,
        method=method,
        headers=headers,
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {"success": False, "errors": [{"message": str(e)}]}


def _smoke() -> dict:
    import subprocess

    out: dict = {}
    for url in (f"https://{ZONE}/", f"https://{ZONE}/news/", f"https://{ZONE}/news/ep01/"):
        try:
            r = subprocess.run(
                ["curl.exe", "-sSI", "--max-time", "25", url],
                capture_output=True,
                text=True,
                timeout=40,
                check=False,
            )
            head = (r.stdout or "") + (r.stderr or "")
            line = next((ln for ln in head.splitlines() if ln.startswith("HTTP/")), "")
            out[url] = {"exit": r.returncode, "status_line": line, "ok": " 200" in line or line.endswith("200")}
        except Exception as exc:
            out[url] = {"ok": False, "error": str(exc)}
    out["all_ok"] = all(v.get("ok") for v in out.values() if isinstance(v, dict) and "ok" in v)
    return out


def main() -> int:
    dry = "--dry-run" in sys.argv
    apply = "--apply" in sys.argv
    smoke_only = "--smoke-only" in sys.argv
    if not (dry or apply or smoke_only):
        dry = True

    doc: dict = {
        "schema": "mudda.mutda_news_open_beta_route_dns_ensure.v0_1",
        "generated_at_utc": _utc(),
        "zone": ZONE,
        "zone_id": ZONE_ID,
        "script": SCRIPT,
        "dry_run": dry,
        "apply": apply,
        "PRODUCT_DONE": False,
        "send_gate": "HOLD",
        "tier3_human_if_403": [
            "dash.cloudflare.com → Workers & Pages → mutda-news-open-beta",
            "Domains / Routes → Add route: mutda.ai/*  and  mutda.ai  (script=mutda-news-open-beta)",
            "또는 Custom domains → Add mutda.ai (DNS 자동 생성 선호)",
            "DNS: apex에 레코드 없으면 AAAA 100:: proxied(주황구름) 추가 후 라우트 연결",
            "토큰 보강: Zone DNS Edit + Workers Routes Edit on mutda.ai → User env MKM_CLOUDFLARE_MUTDA_DNS_ROUTES_TOKEN",
        ],
    }

    if smoke_only:
        doc["smoke"] = _smoke()
        doc["PUBLIC_LIVE"] = bool(doc["smoke"].get("all_ok"))
        OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"ok": doc["PUBLIC_LIVE"], "mode": "smoke_only", "out": str(OUT)}, ensure_ascii=False))
        return 0 if doc["PUBLIC_LIVE"] else 2

    tok, src = resolve_cloudflare_token(extra_keys=TOKEN_EXTRA)
    doc["token_source"] = src
    if not tok:
        doc["error"] = "no_token"
        OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"ok": False, "error": "no_token"}, ensure_ascii=False))
        return 1

    st, pl = _api(tok, "GET", f"/zones/{ZONE_ID}/dns_records?per_page=50")
    doc["dns_list"] = {"http": st, "success": pl.get("success"), "errors": pl.get("errors")}
    if not pl.get("success"):
        doc["blocker"] = "dns_api_403_or_fail"
        doc["OPEN_BETA_READY"] = True
        doc["PUBLIC_LIVE"] = False
        OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"ok": False, "blocker": doc["blocker"], "tier3": True, "out": str(OUT)}, ensure_ascii=False))
        return 3

    recs = pl.get("result") or []
    doc["dns_before"] = [
        {"type": r.get("type"), "name": r.get("name"), "content": r.get("content"), "proxied": r.get("proxied")}
        for r in recs
    ]
    apex = [r for r in recs if r.get("name") == ZONE]
    need_aaaa = not any(r.get("type") == "AAAA" and r.get("proxied") for r in apex)
    need_a = not any(r.get("type") == "A" and r.get("proxied") for r in apex)
    # Prefer AAAA 100:: for workers-only if no origin A
    actions: list[dict] = []
    if need_aaaa and need_a:
        body = {
            "type": "AAAA",
            "name": ZONE,
            "content": AAAA_PLACEHOLDER,
            "proxied": True,
            "ttl": 1,
        }
        actions.append({"dns_create": body})
        if apply and not dry:
            stc, plc = _api(tok, "POST", f"/zones/{ZONE_ID}/dns_records", body)
            actions[-1]["result"] = {"http": stc, "success": plc.get("success"), "errors": plc.get("errors")}

    # routes
    st_r, pl_r = _api(tok, "GET", f"/zones/{ZONE_ID}/workers/routes")
    doc["routes_list"] = {"http": st_r, "success": pl_r.get("success"), "errors": pl_r.get("errors")}
    if not pl_r.get("success"):
        doc["blocker"] = "workers_routes_api_403_or_fail"
        doc["dns_actions"] = actions
        OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"ok": False, "blocker": doc["blocker"], "tier3": True, "out": str(OUT)}, ensure_ascii=False))
        return 4

    existing = {(r.get("pattern"), r.get("script")) for r in (pl_r.get("result") or [])}
    wanted = [(f"{ZONE}/*", SCRIPT), (ZONE, SCRIPT)]
    for pattern, script in wanted:
        if (pattern, script) in existing:
            actions.append({"route": pattern, "status": "exists"})
            continue
        body = {"pattern": pattern, "script": script}
        actions.append({"route_create": body})
        if apply and not dry:
            stc, plc = _api(tok, "POST", f"/zones/{ZONE_ID}/workers/routes", body)
            actions[-1]["result"] = {"http": stc, "success": plc.get("success"), "errors": plc.get("errors")}

    doc["actions"] = actions
    if apply and not dry:
        doc["smoke"] = _smoke()
        live = bool(doc["smoke"].get("all_ok"))
        doc["PUBLIC_LIVE"] = live
        doc["FINAL_STATUS"] = "OPEN_BETA_LIVE" if live else "OPEN_BETA_READY"
        if STATUS.is_file():
            try:
                st_doc = json.loads(STATUS.read_text(encoding="utf-8"))
                st_doc["generated_at_utc"] = _utc()
                st_doc["PUBLIC_LIVE"] = live
                st_doc["OPEN_BETA_LIVE"] = live
                st_doc["OPEN_BETA_READY"] = True
                st_doc["phase_1_complete"] = live
                st_doc["PRODUCT_DONE"] = False
                st_doc["FINAL_STATUS"] = doc["FINAL_STATUS"]
                st_doc["route_dns_ensure"] = str(OUT.relative_to(ROOT)).replace("\\", "/")
                STATUS.write_text(json.dumps(st_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            except Exception as exc:
                doc["status_update_error"] = str(exc)
    else:
        doc["PUBLIC_LIVE"] = False
        doc["note"] = "dry-run only — pass --apply when token has DNS+Routes Edit"

    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": bool(doc.get("PUBLIC_LIVE")) if apply and not dry else True,
                "dry_run": dry,
                "apply": apply and not dry,
                "PUBLIC_LIVE": doc.get("PUBLIC_LIVE"),
                "blocker": doc.get("blocker"),
                "out": str(OUT).replace("\\", "/"),
            },
            ensure_ascii=False,
        )
    )
    if doc.get("blocker"):
        return 3
    if apply and not dry and not doc.get("PUBLIC_LIVE"):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
