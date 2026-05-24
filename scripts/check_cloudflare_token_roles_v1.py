#!/usr/bin/env python3
"""Cloudflare token roles triage — prevent mkmlife vs jemaai rulesets confusion.

Never prints secret values. SSOT report: reports/cloudflare_token_roles_triage_v1_latest.json

  py scripts/check_cloudflare_token_roles_v1.py
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
from mkm_cloudflare_http_probe_v1 import probe_smartfarm_1hop  # noqa: E402
from mkm_cloudflare_token_v1 import (  # noqa: E402
    _read_dotenv_key,
    _read_windows_user_env,
    resolve_cloudflare_jema_ai_redirect_token,
    resolve_cloudflare_token,
    token_fingerprint,
)

OUT = ROOT / "reports" / "cloudflare_token_roles_triage_v1_latest.json"
JEMAAI_ZONE_ID = "cf557dfa09436d998416ad849e73c0ec"
JEMA_AI_ZONE_ID = "e64f17593ce48e31c2839b421c8bd4c0"
MKMLIFE_ZONE_ID = "259a847ea3643566383972ebd3ede918"
JEMAAI_PHASES = ("http_ratelimit", "http_request_cache_settings")
JEMA_AI_REDIRECT_PHASE = "http_request_dynamic_redirect"

RECURRENCE_GUARD_VERSION = "cf_token_roles_v1"


def _token_for_key(key: str) -> tuple[str, str]:
    import os

    v = _read_windows_user_env(key)
    if v:
        return v.strip(), f"user_env:{key}"
    v = os.environ.get(key, "").strip()
    if v:
        return v, f"process_env:{key}"
    v = _read_dotenv_key(key)
    if v:
        return v.strip(), f".env:{key}"
    return "", "missing"


def _verify(tok: str) -> tuple[int, bool]:
    req = urllib.request.Request(
        "https://api.cloudflare.com/client/v4/user/tokens/verify",
        headers={"Authorization": f"Bearer {tok}", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            j = json.loads(resp.read().decode())
            return resp.status, bool(j.get("success"))
    except urllib.error.HTTPError as e:
        try:
            j = json.loads(e.read().decode())
        except Exception:
            j = {}
        return e.code, bool(j.get("success"))


def _zone_get(tok: str, zone_id: str) -> tuple[int, bool]:
    req = urllib.request.Request(
        f"https://api.cloudflare.com/client/v4/zones/{zone_id}",
        headers={"Authorization": f"Bearer {tok}", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            j = json.loads(resp.read().decode())
            return resp.status, bool(j.get("success"))
    except urllib.error.HTTPError as e:
        try:
            j = json.loads(e.read().decode())
        except Exception:
            j = {"success": False}
        return e.code, bool(j.get("success"))


def _rulesets_auth_ok(tok: str) -> tuple[bool, str]:
    for phase in JEMAAI_PHASES:
        path = f"/zones/{JEMAAI_ZONE_ID}/rulesets/phases/{phase}/entrypoint"
        req = urllib.request.Request(
            f"https://api.cloudflare.com/client/v4{path}",
            headers={"Authorization": f"Bearer {tok}", "Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                pl = json.loads(resp.read().decode())
                if pl.get("success"):
                    continue
        except urllib.error.HTTPError as e:
            try:
                pl = json.loads(e.read().decode())
            except Exception:
                pl = {}
            if e.code == 403:
                for err in pl.get("errors") or []:
                    if err.get("code") == 10000:
                        return False, "rulesets_403_code_10000"
            if e.code == 404:
                for err in pl.get("errors") or []:
                    if err.get("code") == 10003:
                        continue
            return False, f"rulesets_http_{e.code}"
        else:
            if not pl.get("success"):
                return False, "rulesets_api_not_success"
    return True, "rulesets_ok"


def _jema_ai_redirect_auth_ok(tok: str) -> tuple[bool, str]:
    path = f"/zones/{JEMA_AI_ZONE_ID}/rulesets/phases/{JEMA_AI_REDIRECT_PHASE}/entrypoint"
    req = urllib.request.Request(
        f"https://api.cloudflare.com/client/v4{path}",
        headers={"Authorization": f"Bearer {tok}", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            pl = json.loads(resp.read().decode())
            if pl.get("success"):
                return True, "jema_ai_redirect_ok"
            return False, "jema_ai_redirect_api_not_success"
    except urllib.error.HTTPError as e:
        try:
            pl = json.loads(e.read().decode())
        except Exception:
            pl = {}
        if e.code in (401, 403):
            for err in pl.get("errors") or []:
                if err.get("code") == 10000:
                    return False, "jema_ai_redirect_403_code_10000"
        return False, f"jema_ai_redirect_http_{e.code}"


def _key_presence() -> dict[str, bool]:
    keys = (
        "MKM_CLOUDFLARE_JEMA_AI_REDIRECT_TOKEN",
        "CLOUDFLARE_RULESETS_API_TOKEN",
        "MKM_CLOUDFLARE_RULESETS_TOKEN",
        "MKM_MKMLIFE_CF_ANALYTICS_TOKEN",
        "CLOUDFLARE_API_TOKEN",
        "CF_API_TOKEN",
    )
    out: dict[str, bool] = {}
    for k in keys:
        tok, _ = _token_for_key(k)
        out[k] = bool(tok)
    return out


def _build_recurrence_guard(
    *,
    rulesets_src: str,
    rulesets_fp: str,
    general_fp: str,
    mkmlife_fp: str,
    rulesets_ready: bool,
    verify_ok: bool,
    rulesets_blocker: str,
) -> dict:
    same_general_and_mkmlife = bool(
        general_fp and mkmlife_fp and general_fp == mkmlife_fp
    )
    rulesets_is_fallback = rulesets_src.endswith("CLOUDFLARE_API_TOKEN") or rulesets_src.endswith(
        "CF_API_TOKEN"
    )
    guard: dict = {
        "version": RECURRENCE_GUARD_VERSION,
        "never_do": [
            "Do not tell the commander to create a new token daily — verify often passes while rulesets return 403 (scope, not expiry).",
            "Do not overwrite CLOUDFLARE_API_TOKEN when fixing jemaai showroom rulesets.",
            "Do not use mkmlife analytics token setup (MKM_MKMLIFE_CF_ANALYTICS_TOKEN) to fix jemaai rulesets API apply.",
        ],
    }
    if rulesets_ready:
        guard["status"] = "ok"
        guard["agent_instruction_ko"] = (
            "CF 토큰 역할 정상. jemaai rulesets 자동화 가능. 새 토큰 생성 안내 금지."
        )
        return guard

    if verify_ok and rulesets_blocker.startswith("rulesets_"):
        guard["status"] = "scope_mismatch_or_missing_rulesets_key"
        guard["misdiagnosis_avoid"] = ["token_expired", "create_new_mkmlife_token", "rotate CLOUDFLARE_API_TOKEN"]
        steps = []
        steps.append(
            "권장(1인): CF 대시보드에서 기존 토큰(cfut_* 지문 동일) 편집 → jemaai.cloud만 "
            "Zone Read + Zone WAF Edit + Cache Rules Edit 추가 후 Cursor 재시작 "
            "(새 토큰 매일 생성 금지). docs/final/JEMAAI_CLOUD_SHOWROOM_CF_EDGE_DASHBOARD_V1.md"
        )
        if not _key_presence().get("CLOUDFLARE_RULESETS_API_TOKEN"):
            steps.append(
                "또는 1회: 전용 토큰 → reports/cloudflare_jemaai_solo_edge_token_secret_LOCAL.json "
                "→ scripts/Invoke-ApplyJemaaiShowroomCfEdgeTokenFromSecret_v1.ps1 "
                "(CLOUDFLARE_RULESETS_API_TOKEN만 갱신, CLOUDFLARE_API_TOKEN 덮어쓰기 금지)"
            )
        else:
            steps.append(
                "CLOUDFLARE_RULESETS_API_TOKEN 값이 WAF+Cache Rules Edit 권한인지 CF 대시보드에서 확인 후 secret apply 재실행"
            )
        if same_general_and_mkmlife:
            steps.append(
                "MKM_MKMLIFE_CF_ANALYTICS_TOKEN 과 CLOUDFLARE_API_TOKEN 동일 지문 — mkmlife UV는 별도 문제 없을 수 있음; jemaai는 RULESETS 키 분리 필수"
            )
        guard["one_time_fix"] = steps
        guard["optional_manual"] = (
            "대시보드 수동 장전 후 공개 probe 15/15면 API 재적용 생략 가능 — "
            "docs/final/JEMAAI_CLOUD_SHOWROOM_CF_EDGE_DASHBOARD_V1.md §재발 방지"
        )
        guard["agent_instruction_ko"] = (
            "토큰 만료가 아니라 권한/키 분리 문제입니다. "
            "CLOUDFLARE_RULESETS_API_TOKEN 1회 설정 또는 수동 엣지 완료 시 '새 토큰' 반복 안내하지 마세요."
        )
        return guard

    guard["status"] = "token_missing_or_invalid"
    guard["agent_instruction_ko"] = "CF API 토큰 없음 또는 verify 실패 — 역할별 triage 표 참고."
    return guard


def _build_jema_ai_redirect_guard(
    *,
    redirect_src: str,
    redirect_fp: str,
    jemaai_rulesets_ready: bool,
    redirect_ready: bool,
    verify_ok: bool,
    redirect_blocker: str,
) -> dict:
    guard: dict = {
        "zone": "jema-ai.com",
        "phase": JEMA_AI_REDIRECT_PHASE,
        "never_do": [
            "Do not use CLOUDFLARE_API_TOKEN alone for jema-ai.com /smartfarm CF redirect — DNS token lacks dynamic redirect rulesets on this zone.",
            "Do not assume jemaai.cloud rulesets OK implies jema-ai.com redirect OK — different zone scope.",
            "Do not repeat PUT when entrypoint GET returns 403 code 10000 — fix token scope once.",
        ],
    }
    if redirect_ready and verify_ok:
        guard["status"] = "ok"
        guard["agent_instruction_ko"] = (
            "jema-ai.com dynamic redirect API 준비됨. smartfarm 1-hop 자동화 가능."
        )
        return guard
    if jemaai_rulesets_ready and verify_ok and not redirect_ready:
        http = probe_smartfarm_1hop()
        if http.get("ok"):
            guard["status"] = "edge_ok_operational_ssot"
            guard["http_probe"] = http
            guard["misdiagnosis_avoid"] = [
                "token_expired",
                "rotate CLOUDFLARE_API_TOKEN",
                "new token daily",
                "ask_commander_to_edit_cf_token_again",
            ]
            guard["agent_instruction_ko"] = (
                "엣지 1-hop 정상(HTTP SSOT). API scope 없음은 만료 아님 — "
                "토큰 편집·대시보드 클릭 반복 안내 금지. 인프라-as-code만 필요 시 LOCAL secret 1회."
            )
            return guard
        guard["status"] = "jemaai_ok_jema_ai_zone_missing"
        guard["misdiagnosis_avoid"] = ["token_expired", "rotate CLOUDFLARE_API_TOKEN", "new token daily"]
        guard["one_time_fix_ko"] = [
            "jemaai.cloud rulesets는 통과했지만 jema-ai.com 존 scope가 없음.",
            "HTTP 1-hop도 실패면 CF Redirect Rules 또는 nginx 폴백 점검.",
            "선택: reports/cloudflare_jema_ai_redirect_token_secret_LOCAL.json → Invoke-ApplyJemaAiRedirectTokenFromSecret_v1.ps1",
        ]
        guard["agent_instruction_ko"] = (
            "만료 아님 — jema-ai.com Rulesets scope 또는 엣지 규칙 필요. HTTP 실패 시에만 엣지 조치."
        )
        return guard
    guard["status"] = "redirect_token_missing_or_invalid"
    guard["agent_instruction_ko"] = "jema-ai redirect 토큰 없음 또는 verify 실패 — triage jema_ai_dynamic_redirect 참고."
    guard["blocker"] = redirect_blocker
    return guard


def main() -> int:
    presence = _key_presence()
    general_tok, general_src = resolve_cloudflare_token()
    rulesets_tok, rulesets_src = resolve_cloudflare_token(
        extra_keys=("CLOUDFLARE_RULESETS_API_TOKEN", "MKM_CLOUDFLARE_RULESETS_TOKEN")
    )
    mkmlife_tok, mkmlife_src = resolve_cloudflare_token(
        extra_keys=("MKM_MKMLIFE_CF_ANALYTICS_TOKEN",)
    )
    if not mkmlife_tok and general_tok:
        mkmlife_tok, mkmlife_src = general_tok, f"fallback:{general_src}"

    roles: dict = {
        "general_dns": {
            "keys": ["CLOUDFLARE_API_TOKEN", "CF_API_TOKEN"],
            "configured": presence["CLOUDFLARE_API_TOKEN"] or presence["CF_API_TOKEN"],
            "resolved_source": general_src,
            "fingerprint": token_fingerprint(general_tok) if general_tok else None,
        },
        "mkmlife_analytics": {
            "keys": ["MKM_MKMLIFE_CF_ANALYTICS_TOKEN"],
            "configured": presence["MKM_MKMLIFE_CF_ANALYTICS_TOKEN"],
            "resolved_source": mkmlife_src,
            "fingerprint": token_fingerprint(mkmlife_tok) if mkmlife_tok else None,
        },
        "jemaai_rulesets": {
            "keys": ["CLOUDFLARE_RULESETS_API_TOKEN", "MKM_CLOUDFLARE_RULESETS_TOKEN"],
            "dedicated_key_set": presence["CLOUDFLARE_RULESETS_API_TOKEN"]
            or presence["MKM_CLOUDFLARE_RULESETS_TOKEN"],
            "resolved_source": rulesets_src,
            "fingerprint": token_fingerprint(rulesets_tok) if rulesets_tok else None,
        },
    }

    verify_st, verify_ok = (0, False)
    if rulesets_tok:
        verify_st, verify_ok = _verify(rulesets_tok)

    mk_zone_ok = False
    if mkmlife_tok:
        _, mk_zone_ok = _zone_get(mkmlife_tok, MKMLIFE_ZONE_ID)

    rulesets_ready = False
    rulesets_blocker = "no_token"
    if rulesets_tok:
        rulesets_ready, rulesets_blocker = _rulesets_auth_ok(rulesets_tok)

    redirect_tok, redirect_src = resolve_cloudflare_jema_ai_redirect_token()
    redirect_verify_st, redirect_verify_ok = (0, False)
    if redirect_tok:
        redirect_verify_st, redirect_verify_ok = _verify(redirect_tok)
    redirect_ready = False
    redirect_blocker = "no_token"
    if redirect_tok:
        redirect_ready, redirect_blocker = _jema_ai_redirect_auth_ok(redirect_tok)
    smartfarm_http = probe_smartfarm_1hop()
    redirect_operational = bool(smartfarm_http.get("ok"))

    shared_fp = (
        roles["general_dns"]["fingerprint"]
        and roles["mkmlife_analytics"]["fingerprint"]
        and roles["general_dns"]["fingerprint"] == roles["mkmlife_analytics"]["fingerprint"]
    )

    out: dict = {
        "schema": "cloudflare_token_roles_triage_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "key_presence": presence,
        "roles": roles,
        "shared_fingerprint_general_and_mkmlife": shared_fp,
        "jemaai_rulesets": {
            "automation_ready": rulesets_ready and verify_ok,
            "token_verify_http": verify_st,
            "token_verify_ok": verify_ok,
            "blocker": rulesets_blocker,
            "uses_fallback_general_token": rulesets_src.endswith("CLOUDFLARE_API_TOKEN")
            or rulesets_src.endswith("CF_API_TOKEN"),
        },
        "jema_ai_dynamic_redirect": {
            "zone_id": JEMA_AI_ZONE_ID,
            "host": "jema-ai.com",
            "automation_ready": redirect_ready and redirect_verify_ok,
            "operational_ready": redirect_operational,
            "http_probe": smartfarm_http,
            "token_source": redirect_src,
            "token_fingerprint": token_fingerprint(redirect_tok) if redirect_tok else None,
            "token_verify_http": redirect_verify_st,
            "token_verify_ok": redirect_verify_ok,
            "blocker": redirect_blocker,
            "smartfarm_script": "scripts/setup_cloudflare_jema_ai_smartfarm_redirect_v1.py",
        },
        "mkmlife_analytics_probe": {
            "zone_read_ok": mk_zone_ok,
        },
        "recurrence_guard": _build_recurrence_guard(
            rulesets_src=rulesets_src,
            rulesets_fp=token_fingerprint(rulesets_tok) if rulesets_tok else "",
            general_fp=token_fingerprint(general_tok) if general_tok else "",
            mkmlife_fp=token_fingerprint(mkmlife_tok) if mkmlife_tok else "",
            rulesets_ready=rulesets_ready and verify_ok,
            verify_ok=verify_ok,
            rulesets_blocker=rulesets_blocker,
        ),
        "jema_ai_redirect_guard": _build_jema_ai_redirect_guard(
            redirect_src=redirect_src,
            redirect_fp=token_fingerprint(redirect_tok) if redirect_tok else "",
            jemaai_rulesets_ready=rulesets_ready and verify_ok,
            redirect_ready=redirect_ready and redirect_verify_ok,
            verify_ok=redirect_verify_ok,
            redirect_blocker=redirect_blocker,
        ),
        "smartfarm_operational": {
            "ready": redirect_operational,
            "http_probe": smartfarm_http,
        },
        "zone_registry_ssot": "docs/final/artifacts/mkm_cloudflare_zone_registry_v1.json",
        "commands": {
            "triage": "py scripts/check_cloudflare_token_roles_v1.py",
            "full_recurrence_bundle": (
                "powershell -NoProfile -ExecutionPolicy Bypass -File "
                "scripts/Invoke-MkmCloudflareRecurrenceGuardBundle_v1.ps1"
            ),
            "zone_audit": "py scripts/audit_mkm_cloudflare_zones_v1.py",
            "jema_ai_smartfarm_redirect": (
                "powershell -File scripts/Invoke-CloudflareJemaAiSmartfarmRedirect_v1.ps1"
            ),
            "apply_rulesets_token_once": (
                "powershell -File scripts/Invoke-ApplyJemaaiShowroomCfEdgeTokenFromSecret_v1.ps1"
            ),
            "open_cf_ui_rulesets": (
                "powershell -File scripts/Open-JemaaiShowroomCfEdgeTokenTemplate_v1.ps1"
            ),
            "mkmlife_only": "powershell -File scripts/Invoke-MkmlifeCfAnalyticsEnvSetup_v1.ps1",
        },
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2, ensure_ascii=False))
    rg = out["recurrence_guard"]
    print(f"\n[recurrence_guard] {rg.get('status')}: {rg.get('agent_instruction_ko', '')}", file=sys.stderr)
    jag = out["jema_ai_redirect_guard"]
    print(
        f"[jema_ai_redirect_guard] {jag.get('status')}: {jag.get('agent_instruction_ko', '')}",
        file=sys.stderr,
    )

    if out["jemaai_rulesets"]["automation_ready"]:
        return 0
    if jag.get("status") == "edge_ok_operational_ssot":
        return 0
    if out["smartfarm_operational"]["ready"]:
        return 0
    if verify_ok and not rulesets_ready:
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
