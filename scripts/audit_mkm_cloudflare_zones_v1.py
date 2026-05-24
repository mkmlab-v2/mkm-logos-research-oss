#!/usr/bin/env python3
"""MKM Cloudflare zone + token scope audit — prevent jemaai.cloud vs jema-ai.com recurrence.

Reads SSOT: docs/final/artifacts/mkm_cloudflare_zone_registry_v1.json
Writes: reports/mkm_cloudflare_zone_audit_v1_latest.json

Never prints secrets.

  py scripts/audit_mkm_cloudflare_zones_v1.py
  py scripts/audit_mkm_cloudflare_zones_v1.py --refresh-inventory
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from mkm_cloudflare_token_v1 import (  # noqa: E402
    resolve_cloudflare_jema_ai_redirect_token,
    resolve_cloudflare_token,
    token_fingerprint,
)

REGISTRY = ROOT / "docs/final/artifacts/mkm_cloudflare_zone_registry_v1.json"
OUT = ROOT / "reports/mkm_cloudflare_zone_audit_v1_latest.json"
INVENTORY = ROOT / "reports/cloudflare_op5_zone_inventory_v1.json"
TRIAGE = ROOT / "reports/cloudflare_token_roles_triage_v1_latest.json"

JEMAAI_ZONE_ID = "cf557dfa09436d998416ad849e73c0ec"
JEMA_AI_ZONE_ID = "e64f17593ce48e31c2839b421c8bd4c0"
JEMAAI_PHASES = ("http_ratelimit", "http_request_cache_settings")
JEMA_AI_REDIRECT_PHASE = "http_request_dynamic_redirect"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_registry() -> dict[str, Any]:
    if not REGISTRY.is_file():
        raise FileNotFoundError(REGISTRY)
    return json.loads(REGISTRY.read_text(encoding="utf-8-sig"))


def _list_zones(tok: str) -> tuple[list[tuple[str, str]], str | None]:
    names: list[tuple[str, str]] = []
    page = 1
    try:
        while True:
            url = f"https://api.cloudflare.com/client/v4/zones?per_page=50&page={page}"
            req = urllib.request.Request(
                url, headers={"Authorization": f"Bearer {tok}", "Accept": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                pl = json.loads(resp.read().decode())
            if not pl.get("success"):
                return [], json.dumps(pl.get("errors") or pl)[:200]
            for z in pl.get("result") or []:
                n, zid = z.get("name"), z.get("id")
                if n and zid:
                    names.append((str(n), str(zid)))
            total_pages = (pl.get("result_info") or {}).get("total_pages", 1)
            if page >= total_pages:
                break
            page += 1
        return names, None
    except urllib.error.HTTPError as e:
        try:
            pl = json.loads(e.read().decode())
        except Exception:
            pl = {}
        return [], f"http_{e.code}:{pl.get('errors')}"


def _phase_get(tok: str, zone_id: str, phase: str) -> tuple[bool, str]:
    path = f"/zones/{zone_id}/rulesets/phases/{phase}/entrypoint"
    req = urllib.request.Request(
        f"https://api.cloudflare.com/client/v4{path}",
        headers={"Authorization": f"Bearer {tok}", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            pl = json.loads(resp.read().decode())
            if pl.get("success"):
                return True, "ok"
            return False, "api_not_success"
    except urllib.error.HTTPError as e:
        try:
            pl = json.loads(e.read().decode())
        except Exception:
            pl = {}
        if e.code in (401, 403):
            for err in pl.get("errors") or []:
                if err.get("code") == 10000:
                    return False, "403_code_10000_scope"
        if e.code == 404:
            for err in pl.get("errors") or []:
                if err.get("code") == 10003:
                    return True, "ok_no_entrypoint_yet"
        return False, f"http_{e.code}"


def _curl_probe(probe: dict[str, Any]) -> dict[str, Any]:
    url = probe["url"]
    method = probe.get("method", "HEAD")
    cmd = [
        "curl.exe",
        "-sSI",
        "-X",
        method,
        "--max-redirs",
        "0",
        url,
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=False)
    except (subprocess.TimeoutExpired, OSError) as e:
        return {"id": probe.get("id"), "url": url, "ok": False, "error": str(e)}
    text = proc.stdout or ""
    status_m = re.search(r"HTTP/\S+\s+(\d+)", text)
    status = int(status_m.group(1)) if status_m else 0
    loc_m = re.search(r"(?i)^location:\s*(\S+)\s*$", text, re.MULTILINE)
    location = loc_m.group(1).strip() if loc_m else ""
    expect_status = set(probe.get("expect_status") or [200])
    ok = status in expect_status
    prefix = probe.get("expect_location_prefix")
    if prefix and location:
        ok = ok and location.startswith(prefix)
    forbid = probe.get("forbid_location_contains") or []
    for bad in forbid:
        if bad and bad in location:
            ok = False
    return {
        "id": probe.get("id"),
        "url": url,
        "ok": ok,
        "http_status": status,
        "location": location,
        "exit_code": proc.returncode,
    }


def _registry_zones_by_name(reg: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for z in reg.get("zones") or []:
        name = z.get("name")
        if name and z.get("zone_id"):
            out[str(name)] = z
    return out


def _refresh_inventory(tok: str) -> None:
    zones, err = _list_zones(tok)
    doc = {
        "schema": "cloudflare_op5_zone_inventory_v1",
        "generated_at_utc": _utc(),
        "zones": zones,
        "list_error": err,
    }
    INVENTORY.parent.mkdir(parents=True, exist_ok=True)
    INVENTORY.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--refresh-inventory", action="store_true")
    args = ap.parse_args()

    reg = _load_registry()
    reg_zones = _registry_zones_by_name(reg)

    general_tok, general_src = resolve_cloudflare_token()
    rulesets_tok, rulesets_src = resolve_cloudflare_token(
        extra_keys=("CLOUDFLARE_RULESETS_API_TOKEN", "MKM_CLOUDFLARE_RULESETS_TOKEN")
    )
    redirect_tok, redirect_src = resolve_cloudflare_jema_ai_redirect_token()

    if args.refresh_inventory and general_tok:
        _refresh_inventory(general_tok)

    api_visible: dict[str, str] = {}
    list_err: str | None = None
    if general_tok:
        pairs, list_err = _list_zones(general_tok)
        api_visible = {n: zid for n, zid in pairs}

    zone_rows: list[dict[str, Any]] = []
    for name, zdef in sorted(reg_zones.items()):
        expected_id = str(zdef.get("zone_id") or "")
        visible_id = api_visible.get(name)
        id_match = visible_id == expected_id if visible_id else None
        row: dict[str, Any] = {
            "zone": name,
            "zone_id_ssot": expected_id,
            "visible_on_general_token": visible_id is not None,
            "general_token_zone_id": visible_id,
            "zone_id_matches_ssot": id_match,
            "mkm_role": zdef.get("mkm_role"),
        }
        zone_rows.append(row)

    token_matrix = {
        "general_dns": {
            "source": general_src,
            "fingerprint": token_fingerprint(general_tok) if general_tok else None,
            "zone_list_ok": bool(api_visible) and not list_err,
            "list_error": list_err,
        },
        "jemaai_rulesets": {
            "source": rulesets_src,
            "fingerprint": token_fingerprint(rulesets_tok) if rulesets_tok else None,
            "probes": {},
        },
        "jema_ai_redirect": {
            "source": redirect_src,
            "fingerprint": token_fingerprint(redirect_tok) if redirect_tok else None,
            "probes": {},
        },
    }
    if rulesets_tok:
        for phase in JEMAAI_PHASES:
            ok, why = _phase_get(rulesets_tok, JEMAAI_ZONE_ID, phase)
            token_matrix["jemaai_rulesets"]["probes"][f"jemaai.cloud:{phase}"] = {
                "ok": ok,
                "detail": why,
            }
    if redirect_tok:
        ok, why = _phase_get(redirect_tok, JEMA_AI_ZONE_ID, JEMA_AI_REDIRECT_PHASE)
        token_matrix["jema_ai_redirect"]["probes"][f"jema-ai.com:{JEMA_AI_REDIRECT_PHASE}"] = {
            "ok": ok,
            "detail": why,
        }

    http_results: list[dict[str, Any]] = []
    for z in reg.get("zones") or []:
        for probe in z.get("http_probes") or []:
            if probe.get("url"):
                http_results.append(_curl_probe(probe))

    jemaai_api_ok = all(
        p.get("ok") for p in token_matrix["jemaai_rulesets"].get("probes", {}).values()
    ) if rulesets_tok else False
    jema_ai_api_ok = (
        token_matrix["jema_ai_redirect"]["probes"]
        .get(f"jema-ai.com:{JEMA_AI_REDIRECT_PHASE}", {})
        .get("ok", False)
    )
    smartfarm_probe = next((p for p in http_results if p.get("id") == "smartfarm_1hop"), None)
    smartfarm_http_ok = bool(smartfarm_probe and smartfarm_probe.get("ok"))

    gaps: list[str] = []
    if rulesets_tok and not jemaai_api_ok:
        gaps.append("jemaai.cloud_rulesets_api_not_ready")
    if redirect_tok and not jema_ai_api_ok and smartfarm_http_ok:
        gaps.append("jema_ai_redirect_api_scope_missing_but_edge_ok_dashboard")
    if redirect_tok and not jema_ai_api_ok and not smartfarm_http_ok:
        gaps.append("jema_ai_smartfarm_needs_cf_redirect_rule_or_token_scope")
    if not smartfarm_http_ok:
        gaps.append("smartfarm_http_probe_failed")

    edge_only_gap = bool(gaps) and all(
        g == "jema_ai_redirect_api_scope_missing_but_edge_ok_dashboard" for g in gaps
    )
    if edge_only_gap:
        recurrence_status = "ok_edge_operational"
        agent_ko = (
            "엣지 1-hop(smartfarm→farm) 정상 — 운영 SSOT 충족. "
            "API scope 갭은 인프라-as-code 선택사항; 지휘관 토큰 편집 반복 안내 금지(CENTRAL·브라우저 3단계)."
        )
    elif not gaps:
        recurrence_status = "ok"
        agent_ko = "CF 존·토큰 정상."
    else:
        recurrence_status = "action_needed"
        agent_ko = (
            "갭 있음 — reports/mkm_cloudflare_zone_audit_v1_latest.json 의 gaps·token_matrix 확인."
        )
    recurrence = {
        "status": recurrence_status,
        "gaps": gaps,
        "edge_operational_ssot": edge_only_gap,
        "never_confuse_ko": [
            "jemaai.cloud WAF/Cache 통과 ≠ jema-ai.com /smartfarm API 자동화 가능",
            "CLOUDFLARE_API_TOKEN verify 200 ≠ 모든 존 rulesets 편집 가능",
            "HTTP 1-hop OK이면 토큰 편집 없이 운영 완료 — API는 선택",
        ],
        "agent_instruction_ko": agent_ko,
    }

    out_doc: dict[str, Any] = {
        "schema": "mkm_cloudflare_zone_audit_v1",
        "generated_at_utc": _utc(),
        "registry_path": str(REGISTRY.relative_to(ROOT)),
        "zone_inventory_path": str(INVENTORY.relative_to(ROOT)),
        "api_zones_visible_count": len(api_visible),
        "registry_zones_with_id": len(reg_zones),
        "zones": zone_rows,
        "token_matrix": token_matrix,
        "http_probes": http_results,
        "summary": {
            "jemaai_rulesets_api_ready": jemaai_api_ok,
            "jema_ai_redirect_api_ready": jema_ai_api_ok,
            "smartfarm_1hop_http_ok": smartfarm_http_ok,
            "edge_ok_api_gap": smartfarm_http_ok and not jema_ai_api_ok,
            "operational_ok": smartfarm_http_ok,
        },
        "confusion_pairs": reg.get("confusion_pairs"),
        "recurrence_guard": recurrence,
        "commands": reg.get("audit_commands"),
    }

    if TRIAGE.is_file():
        try:
            triage = json.loads(TRIAGE.read_text(encoding="utf-8-sig"))
            out_doc["triage_snapshot"] = {
                "generated_at_utc": triage.get("generated_at_utc"),
                "jemaai_rulesets_ready": (triage.get("jemaai_rulesets") or {}).get("automation_ready"),
                "jema_ai_redirect_ready": (triage.get("jema_ai_dynamic_redirect") or {}).get(
                    "automation_ready"
                ),
                "jema_ai_redirect_guard_status": (triage.get("jema_ai_redirect_guard") or {}).get(
                    "status"
                ),
            }
        except json.JSONDecodeError:
            pass

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out_doc, ensure_ascii=False, indent=2))
    print(
        f"\n[recurrence] {recurrence['status']}: {recurrence['agent_instruction_ko']}",
        file=sys.stderr,
    )
    if edge_only_gap:
        return 0
    if gaps and smartfarm_http_ok:
        return 2
    if gaps:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
