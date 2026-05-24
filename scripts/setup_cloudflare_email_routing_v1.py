#!/usr/bin/env python3
"""Enable Cloudflare Email Routing and forward a custom address (e.g. support@mkmlife.com).

Policy (repo default): keep apex MX for Cloudflare Email Routing only. Do not revert MX to
Hostinger webmail for the same apex (mutually exclusive; Hostinger "incorrect MX" notices
when intentional). See docs/final/NO1KMEDI_MKMLIFE_REPO_PATH_SSOT_2026-04-08.md section 1.3.

Recommended order (same as dashboard; API mirrors this when token is sufficient):
  1) Dashboard: Email Routing → Destination addresses → add/verify ``MKM_MKMLIFE_SUPPORT_FORWARD_TO``
     (inbox link until status is verified, not pending).
  2) Dashboard: Routing rules → create custom address ``{local}@{apex}`` → Send to email → pick verified destination → Save.
  3) Optional: re-run this script with a token that has Email Routing scopes so the flow is repeatable from CI.

Requires API token with Account Email Routing Addresses Edit + Zone Email Routing Rules Edit
(and Zone Read). DNS-only tokens are not enough.

Env:
  CLOUDFLARE_API_TOKEN or CF_API_TOKEN
  MKM_MKMLIFE_SUPPORT_FORWARD_TO — destination inbox (default admin@no1kmedi.com)
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
        key = key.strip()
        val = val.strip().strip('"').strip("'")
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
    headers = {
        "Authorization": f"Bearer {tok}",
        "Accept": "application/json",
    }
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
            return resp.status, payload
    except urllib.error.HTTPError as e:
        try:
            payload = json.loads(e.read().decode("utf-8"))
        except Exception:
            payload = {"success": False, "errors": [{"message": str(e)}]}
        return e.code, payload


def _zone_lookup(tok: str, apex: str) -> dict[str, Any] | None:
    enc = urllib.parse.quote(apex, safe="")
    status, payload = _api(tok, "GET", f"/zones?name={enc}&status=active")
    if not payload.get("success"):
        return None
    rows = payload.get("result") or []
    for z in rows:
        if (z.get("name") or "").lower() == apex.lower():
            return z
    return None


def _cloudflare_auth_hint(errors: Any) -> str | None:
    if not isinstance(errors, list):
        return None
    for e in errors:
        if not isinstance(e, dict):
            continue
        code = e.get("code")
        msg = str(e.get("message") or "").lower()
        if code == 10000 or "authentication error" in msg:
            return (
                "Cloudflare API code 10000(Authentication error): 토큰 재발급, "
                ".env의 CLOUDFLARE_API_TOKEN/CF_API_TOKEN 앞뒤 공백·따옴표 제거 확인. "
                "User 동기화: projects/bitcoin-trading/ops/windows-rehearsal/sync_required_env_to_user.ps1"
            )
    return None


def _prepend_auth_hint(manual: list[str], payload: dict[str, Any]) -> None:
    hint = _cloudflare_auth_hint(payload.get("errors"))
    if hint:
        manual.insert(0, hint)


def main() -> int:
    _load_dotenv_token()
    ap = argparse.ArgumentParser(description="Cloudflare Email Routing setup (forward one address).")
    ap.add_argument("--apex", default="mkmlife.com")
    ap.add_argument("--local-part", default="support", help="Local part before @apex")
    ap.add_argument(
        "--forward-to",
        default=os.environ.get("MKM_MKMLIFE_SUPPORT_FORWARD_TO", "admin@no1kmedi.com").strip(),
    )
    ap.add_argument("--zone-id", default="", help="Optional zone id if list zones is scoped away")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--out-json",
        default=os.path.join(
            os.environ.get("MKM_WORKSPACE_ROOT", r"C:\workspace"),
            "reports",
            "cloudflare_email_routing_setup_latest.json",
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
    custom = f"{args.local_part.strip()}@{apex}"
    forward_to = args.forward_to.strip()
    if not forward_to or "@" not in forward_to:
        print("--forward-to must be a full email address", file=sys.stderr)
        return 1

    out: dict[str, Any] = {
        "schema": "cloudflare_email_routing_setup_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "apex": apex,
        "custom_address": custom,
        "forward_to": forward_to,
        "dry_run": args.dry_run,
        "steps": [],
    }

    zone: dict[str, Any] | None = None
    zid = args.zone_id.strip()
    if zid:
        st, pl = _api(tok, "GET", f"/zones/{zid}")
        if pl.get("success") and pl.get("result"):
            zone = pl["result"]
        out["steps"].append({"step": "zone_by_id", "http": st, "zone_id": zid, "ok": zone is not None})
        if not zone:
            zone = {"id": zid, "name": apex, "account_id": os.environ.get("MKM_CLOUDFLARE_ACCOUNT_ID", "").strip() or None}
            out["steps"].append({"step": "zone_by_id_trust_cli", "zone_id": zid, "note": "GET /zones/{id} denied; proceeding with --zone-id"})
    else:
        zone = _zone_lookup(tok, apex)
        out["steps"].append(
            {
                "step": "zone_lookup",
                "ok": zone is not None,
                "zone_id": zone.get("id") if zone else None,
                "zone_status": zone.get("status") if zone else None,
            }
        )

    if not zone or not zone.get("id"):
        out["blocked"] = "zone_not_visible"
        out["manual"] = [
            f"Cloudflare 대시보드 → Websites에 {apex} 가 있는지 확인.",
            "없으면: 도메인 이전(Cloudflare Registrar) 완료 대기 또는 Websites → Add site.",
            "zone_id 확인 후: py scripts/setup_cloudflare_email_routing_v1.py --zone-id <id>",
            "API 토큰에 Email Routing 권한 + 해당 zone 포함 필요.",
        ]
        _write_report(args.out_json, out)
        print(f"BLOCKED: zone {apex} not visible to API token")
        for line in out["manual"]:
            print(f"  - {line}")
        return 2

    zid = zone["id"]
    account_id = (
        (zone.get("account") or {}).get("id")
        or zone.get("account_id")
        or os.environ.get("MKM_CLOUDFLARE_ACCOUNT_ID", "").strip()
    )
    out["zone_id"] = zid
    out["account_id"] = account_id

    st, pl = _api(tok, "GET", f"/zones/{zid}/email/routing")
    routing = pl.get("result") if pl.get("success") else None
    out["steps"].append(
        {"step": "routing_get", "http": st, "success": pl.get("success"), "errors": pl.get("errors"), "result": routing}
    )
    if not pl.get("success"):
        out["blocked"] = "routing_get_failed"
        out["manual"] = [
            "토큰에 Zone Email Routing Rules + Account Email Routing Addresses 권한이 있는지 확인(DNS 전용 토큰 불가).",
            "권장: 대시보드에서 1) 대상 주소 검증 2) 라우팅 규칙 저장 후, 권한 있는 토큰으로 본 스크립트 재실행.",
        ]
        _prepend_auth_hint(out["manual"], pl)
        _write_report(args.out_json, out)
        print("routing GET failed", pl.get("errors"), file=sys.stderr)
        return 3

    if args.dry_run:
        out["action"] = "dry_run_only"
        _write_report(args.out_json, out)
        print(f"DRY-RUN ok zone_id={zid} custom={custom} -> {forward_to}")
        return 0

    if not routing or not routing.get("enabled"):
        st, pl = _api(tok, "POST", f"/zones/{zid}/email/routing/enable", {})
        out["steps"].append(
            {
                "step": "routing_enable",
                "http": st,
                "success": pl.get("success"),
                "errors": pl.get("errors"),
                "result": pl.get("result"),
            }
        )
        if not pl.get("success"):
            out["blocked"] = "routing_enable_failed"
            out["manual"] = [
                "403 등: 토큰에 Zone · Email Routing(Enable) + Account · Email Routing Addresses 권한 추가.",
                "권장(대시보드 우선): 이메일 라우팅 → 대상 주소 검증 → 라우팅 규칙에서 "
                f"{custom} → {forward_to} 저장. 이후 API는 읽기/감사용으로만 써도 됨.",
            ]
            _prepend_auth_hint(out["manual"], pl)
            _write_report(args.out_json, out)
            print("enable failed", pl.get("errors"), file=sys.stderr)
            return 3

    if not account_id:
        out["blocked"] = "account_id_missing"
        out["manual"] = [
            "zone 응답에 account id가 없음: --zone-id 로 조회한 zone 또는 MKM_CLOUDFLARE_ACCOUNT_ID 환경 변수 설정.",
        ]
        _write_report(args.out_json, out)
        return 7

    st, pl = _api(tok, "GET", f"/accounts/{account_id}/email/routing/addresses")
    addresses = pl.get("result") if pl.get("success") else []
    dest = next(
        (a for a in addresses if (a.get("email") or "").lower() == forward_to.lower()),
        None,
    )
    if not dest:
        st, pl = _api(
            tok,
            "POST",
            f"/accounts/{account_id}/email/routing/addresses",
            {"email": forward_to},
        )
        out["steps"].append(
            {
                "step": "destination_create",
                "http": st,
                "success": pl.get("success"),
                "errors": pl.get("errors"),
                "result": pl.get("result"),
            }
        )
        if pl.get("success") and pl.get("result"):
            dest = pl["result"]
        elif not pl.get("success"):
            out["blocked"] = "destination_create_failed"
            out["manual"] = [
                f"대시보드 → 이메일 라우팅 → 대상 주소에서 {forward_to} 추가 후 수신함 링크로 검증.",
                "API 토큰에 Account Email Routing Addresses Edit 포함 여부 확인.",
            ]
            _write_report(args.out_json, out)
            print("destination create failed", pl.get("errors"), file=sys.stderr)
            return 4
    else:
        out["steps"].append({"step": "destination_exists", "email": forward_to, "verified": dest.get("verified")})

    verified = bool(dest and dest.get("verified"))
    out["destination_verified"] = verified
    if not verified:
        out["blocked"] = "destination_not_verified"
        out["manual"] = [
            f"{forward_to} 수신함에서 Cloudflare 확인 메일 링크 클릭.",
            "대시보드 대상 주소 목록에서 상태가 검증 완료인지 확인.",
            "확인 후 동일 명령 재실행(또는 라우팅 규칙만 대시보드에서 저장).",
        ]
        _write_report(args.out_json, out)
        print(f"PENDING: verify destination {forward_to} in inbox, then re-run")
        return 5

    st, pl = _api(tok, "GET", f"/zones/{zid}/email/routing/rules")
    rules = pl.get("result") if pl.get("success") else []
    existing = next(
        (
            r
            for r in rules
            if any(
                m.get("type") == "literal"
                and (m.get("value") or "").lower() == custom.lower()
                for m in (r.get("matchers") or [])
            )
        ),
        None,
    )
    if existing:
        out["steps"].append({"step": "rule_exists", "rule_id": existing.get("id"), "enabled": existing.get("enabled")})
        out["action"] = "already_configured"
        _write_report(args.out_json, out)
        print(f"OK: rule already exists for {custom} -> {forward_to}")
        return 0

    body = {
        "name": f"forward {custom}",
        "enabled": True,
        "matchers": [{"type": "literal", "field": "to", "value": custom}],
        "actions": [{"type": "forward", "value": [forward_to]}],
    }
    st, pl = _api(tok, "POST", f"/zones/{zid}/email/routing/rules", body)
    out["steps"].append(
        {
            "step": "rule_create",
            "http": st,
            "success": pl.get("success"),
            "errors": pl.get("errors"),
            "result": pl.get("result"),
        }
    )
    if not pl.get("success"):
        out["blocked"] = "rule_create_failed"
        out["manual"] = [
            "대상 주소가 대시보드에서 검증 완료인지 확인(미검증이면 규칙 저장이 막히거나 API 실패).",
            f"대시보드 → 라우팅 규칙 → 사용자 설정 주소 {custom} → 이메일로 보내기 → {forward_to} → 저장.",
        ]
        _write_report(args.out_json, out)
        print("rule create failed", pl.get("errors"), file=sys.stderr)
        return 6

    out["action"] = "rule_created"
    _write_report(args.out_json, out)
    print(f"OK: {custom} -> {forward_to}")
    return 0


def _write_report(path: str, data: dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Wrote {path}")


if __name__ == "__main__":
    raise SystemExit(main())
