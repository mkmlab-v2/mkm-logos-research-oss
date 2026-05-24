#!/usr/bin/env python3
"""Probe if token can read/write jemaai.cloud http_ratelimit + cache_settings rulesets entrypoints."""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from mkm_cloudflare_token_v1 import (  # noqa: E402
    _read_dotenv_key,
    _read_windows_user_env,
    resolve_cloudflare_token,
    token_fingerprint,
)

ZONE_ID = "cf557dfa09436d998416ad849e73c0ec"
OUT = ROOT / "reports" / "jemaai_cloud_cf_rules_token_check_v1_latest.json"
PHASES = ("http_ratelimit", "http_request_cache_settings")


def _api(tok: str, method: str, path: str) -> tuple[int, dict]:
    req = urllib.request.Request(
        f"https://api.cloudflare.com/client/v4{path}",
        method=method,
        headers={"Authorization": f"Bearer {tok}", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {"success": False, "errors": [{"message": str(e)}]}


def main() -> int:
    tok, src = resolve_cloudflare_token(
        extra_keys=("CLOUDFLARE_RULESETS_API_TOKEN", "MKM_CLOUDFLARE_RULESETS_TOKEN")
    )
    out: dict = {
        "schema": "jemaai_cloud_cf_rules_token_check_v1",
        "zone": "jemaai.cloud",
        "zone_id": ZONE_ID,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "token_source": src,
        "token_fingerprint": token_fingerprint(tok) if tok else "",
        "phases": {},
        "automation_ready": False,
    }
    if not tok:
        out["error"] = "No token: set CLOUDFLARE_RULESETS_API_TOKEN (User env) or CLOUDFLARE_API_TOKEN"
        OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
        print(json.dumps(out, indent=2))
        return 1

    st, verify = _api(tok, "GET", "/user/tokens/verify")
    out["token_verify"] = {"http": st, "success": bool(verify.get("success"))}

    def _auth_ok(code: int, pl: dict) -> bool:
        if pl.get("success"):
            return True
        if code == 403:
            return False
        for err in pl.get("errors") or []:
            if err.get("code") == 10000:
                return False
        # 404 entrypoint missing = token can call API; apply will PUT-create
        if code == 404 and any((e.get("code") == 10003 for e in (pl.get("errors") or []))):
            return True
        return False

    all_ok = True
    for phase in PHASES:
        ep = f"/zones/{ZONE_ID}/rulesets/phases/{phase}/entrypoint"
        code, pl = _api(tok, "GET", ep)
        ok = _auth_ok(code, pl)
        out["phases"][phase] = {
            "http": code,
            "success": ok,
            "entrypoint_exists": bool(pl.get("success")),
            "rule_count": len((pl.get("result") or {}).get("rules") or []) if pl.get("success") else 0,
            "errors": pl.get("errors"),
        }
        if not ok:
            all_ok = False

    out["automation_ready"] = all_ok and out["token_verify"]["success"]

    cap_paths = {
        "zone_read": f"/zones/{ZONE_ID}",
        "rulesets_list": f"/zones/{ZONE_ID}/rulesets",
        "rulesets_phase_ratelimit": f"/zones/{ZONE_ID}/rulesets/phases/http_ratelimit/entrypoint",
        "rulesets_phase_cache": f"/zones/{ZONE_ID}/rulesets/phases/http_request_cache_settings/entrypoint",
    }
    caps: dict = {}
    for key, path in cap_paths.items():
        code, pl = _api(tok, "GET", path)
        caps[key] = {"http": code, "success": bool(pl.get("success"))}
    out["capability_probe"] = caps
    if not out["automation_ready"]:
        missing = []
        if not caps.get("rulesets_phase_ratelimit", {}).get("success"):
            missing.append(
                "Permissions: 왼쪽=Zone(영역) 그룹 → WAF/Zone WAF → Edit; "
                "또는 기존 mkmlab 토큰 편집(A). UI에 항목 없음=빈 커스텀 토큰 포기"
            )
        if not caps.get("rulesets_phase_cache", {}).get("success"):
            missing.append(
                "Permissions: Zone→Cache Rules Edit + Account→Account Rulesets Edit; "
                "대시보드 수동(B) 가능"
            )
        if caps.get("zone_read", {}).get("success") and missing:
            out["edit_existing_token_note"] = (
                "Zone Read is OK on this token; add the missing rows on the SAME token "
                "(cfut_* fingerprint unchanged). Do not rotate token value for path B."
            )
        out["missing_cf_ui_permissions"] = missing

    out["next_if_ready"] = "py scripts/apply_jemaai_cloud_showroom_cf_edge_rules_v1.py"
    out["next_if_blocked"] = (
        "KR UI: Zone 리소스 3행 — 가운데 검색: Zone Read, Zone WAF, Cache Rules (각 Edit/Read). "
        "가운데 ‘영역 WAF’ 트리 메뉴 없음=검색 UI. "
        "(not Cache Settings / not Zone Rulesets) on jemaai.cloud only. "
        "See docs/final/JEMAAI_CLOUD_SHOWROOM_CF_EDGE_DASHBOARD_V1.md §자동화"
    )
    if not out["automation_ready"]:
        dedicated = bool(_read_dotenv_key("CLOUDFLARE_RULESETS_API_TOKEN")) or bool(
            _read_windows_user_env("CLOUDFLARE_RULESETS_API_TOKEN")
        )
        out["recurrence_guard"] = {
            "run_triage": "py scripts/check_cloudflare_token_roles_v1.py",
            "not_expired_if_verify_ok": out["token_verify"].get("success"),
            "likely_issue": "scope_mismatch_or_missing_CLOUDFLARE_RULESETS_API_TOKEN"
            if out["token_verify"].get("success")
            else "missing_or_invalid_token",
            "never": [
                "overwrite CLOUDFLARE_API_TOKEN for jemaai rulesets",
                "create new mkmlife token when only jemaai apply fails",
                "say token expired daily when verify success=true",
            ],
            "one_time_fix": (
                "powershell -File scripts/Invoke-ApplyJemaaiShowroomCfEdgeTokenFromSecret_v1.ps1"
                if not dedicated
                else "re-save RULESETS token with WAF+Cache Rules Edit on jemaai.cloud"
            ),
        }

    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))
    return 0 if out["automation_ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
