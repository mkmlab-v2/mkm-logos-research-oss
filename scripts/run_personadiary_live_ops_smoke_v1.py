#!/usr/bin/env python3
"""PersonaDiary live ops smoke — apex + moment API (Phase B). Writes JSON reports."""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import personadiary_consumer_copy_v1 as pd_copy  # noqa: E402

UA = "MKM-PersonadiarySmoke/1.0"
APEX = "https://personadiary.com"

HUB_FOOTER_MARKERS = (
    "pd-hub-footer",
    "MKM 관련 제품",
    "JEMA AI 브랜드",
    "mkmlife.com",
)
HUB_FOOTER_BOUNDARY = "합치지 않습니다"

COMMERCIAL_HTML_MARKERS = (
    "pd-commercial-home-v1",
    "pd-moment-nation-hero",
    "moment-meal-menu-v1",
    "pd-acode-persona-v1",
    "세상 속의 나",
    "persona-visual-card-v1",
    "pd-moment-quota-v1",
    "pd-plus-teaser",
)

PHASE2_HTML_MARKERS = (
    "pd-ritual-draw",
    "pd-ritual-status-slot",
    "Lattice Convergence",
    "빛의 구슬",
)
PHASE2_LUT_SCHEMA = "personadiary_ritual_draw_lut_major22_v1"
PHASE2_BLOOM_SCHEMA = "magic_orb_graph_bloom_v1"
OPS_HTML_MARKERS = (
    "pd-main-ops",
    "pd-ops-commercial-v1",
    "Persona Diary",
    "pd-ops-export",
    "pd-ops-import",
    "pd-ops-cache-hint",
    "pd-ops-native-hypo",
    "pd-ops-native-intent-hypo",
    "pd-ops-voice-hypo",
    "pd-ops-fab-v1",
    "pd-android-edge-to-edge-v1",
)


def hub_footer_probe_ok(html: str) -> tuple[bool, str]:
    """Design polish: MKM family hub footer on apex HTML (preview_only boundary)."""
    missing = [m for m in HUB_FOOTER_MARKERS if m not in html]
    if missing:
        return False, f"missing markers: {', '.join(missing)}"
    if HUB_FOOTER_BOUNDARY not in html:
        return False, f"missing boundary copy: {HUB_FOOTER_BOUNDARY}"
    return True, f"markers ok ({', '.join(HUB_FOOTER_MARKERS)})"


def _fetch(
    url: str,
    *,
    method: str = "GET",
    body: dict | None = None,
    timeout: int = 25,
) -> dict:
    headers = {"User-Agent": UA, "Accept": "*/*"}
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            text = resp.read().decode("utf-8", errors="replace")
            return {"ok": True, "status": resp.status, "text": text}
    except urllib.error.HTTPError as e:
        text = e.read().decode("utf-8", errors="replace") if e.fp else ""
        return {"ok": False, "status": e.code, "text": text, "error": str(e)}
    except Exception as e:
        return {"ok": False, "status": 0, "text": "", "error": str(e)}


def _fetch_no_redirect(url: str, *, timeout: int = 20) -> dict:
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    opener = urllib.request.build_opener(NoRedirect)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"}, method="GET")
    try:
        with opener.open(req, timeout=timeout) as resp:
            return {
                "ok": True,
                "status": resp.status,
                "location": resp.headers.get("Location", ""),
            }
    except urllib.error.HTTPError as e:
        return {
            "ok": False,
            "status": e.code,
            "location": e.headers.get("Location", "") if e.headers else "",
            "error": str(e),
        }
    except Exception as e:
        return {"ok": False, "status": 0, "location": "", "error": str(e)}


def main() -> int:
    probes: dict[str, dict] = {}

    page = _fetch(f"{APEX}/")
    page_text = page.get("text") or ""
    probes["apex_page"] = {
        "url": f"{APEX}/",
        "status": page.get("status"),
        "ok": page.get("ok") and page.get("status") == 200
        and "Persona Diary" in page_text,
    }

    ops_page = _fetch(f"{APEX}/ops")
    ops_text = ops_page.get("text") or ""
    ops_missing = [m for m in OPS_HTML_MARKERS if m not in ops_text]
    probes["mobile_ops_page"] = {
        "url": f"{APEX}/ops",
        "status": ops_page.get("status"),
        "ok": ops_page.get("ok") and ops_page.get("status") == 200 and not ops_missing,
        "detail": (
            f"markers ok ({', '.join(OPS_HTML_MARKERS)})"
            if not ops_missing
            else f"missing: {', '.join(ops_missing)}"
        ),
    }

    pd_ops_redirect = _fetch_no_redirect(f"{APEX}/personadiary/ops")
    home_redirect = _fetch_no_redirect(f"{APEX}/home")
    favicon = _fetch(f"{APEX}/favicon.ico")
    probes["apex_route_canonical"] = {
        "url": APEX,
        "ok": (
            pd_ops_redirect.get("status") == 308
            and str(pd_ops_redirect.get("location") or "").rstrip("/").endswith("/ops")
            and home_redirect.get("status") == 308
            and favicon.get("ok")
            and favicon.get("status") == 200
        ),
        "detail": (
            f"personadiary/ops→{pd_ops_redirect.get('status')} {pd_ops_redirect.get('location')}; "
            f"home→{home_redirect.get('status')}; favicon→{favicon.get('status')}"
        ),
    }

    manifest = _fetch(f"{APEX}/personadiary/manifest.webmanifest")
    manifest_ok = False
    if manifest.get("ok") and manifest.get("status") == 200:
        try:
            mj = json.loads(manifest["text"])
            manifest_ok = mj.get("start_url") == "/ops"
        except json.JSONDecodeError:
            manifest_ok = False
    probes["pwa_manifest"] = {
        "url": f"{APEX}/personadiary/manifest.webmanifest",
        "status": manifest.get("status"),
        "ok": manifest_ok,
    }

    hub_ok, hub_detail = hub_footer_probe_ok(page_text)
    probes["design_hub_footer"] = {
        "url": f"{APEX}/",
        "ok": page.get("ok") and page.get("status") == 200 and hub_ok,
        "detail": hub_detail,
    }

    phase2_missing = [m for m in PHASE2_HTML_MARKERS if m not in page_text]
    probes["phase2_ritual_lattice_html"] = {
        "url": f"{APEX}/",
        "ok": page.get("ok") and page.get("status") == 200 and not phase2_missing,
        "detail": (
            f"markers ok ({', '.join(PHASE2_HTML_MARKERS)})"
            if not phase2_missing
            else f"missing: {', '.join(phase2_missing)}"
        ),
    }

    commercial_missing = [m for m in COMMERCIAL_HTML_MARKERS if m not in page_text]
    probes["commercial_home_html"] = {
        "url": f"{APEX}/",
        "ok": page.get("ok") and page.get("status") == 200 and not commercial_missing,
        "detail": (
            f"markers ok ({', '.join(COMMERCIAL_HTML_MARKERS)})"
            if not commercial_missing
            else f"missing: {', '.join(commercial_missing)}"
        ),
    }

    lut_fetch = _fetch(f"{APEX}/data/personadiary_ritual_draw_lut_major22_v1.json")
    lut_ok = False
    if lut_fetch.get("ok") and lut_fetch.get("status") == 200:
        try:
            lut_doc = json.loads(lut_fetch["text"])
            lut_ok = (
                lut_doc.get("schema") == PHASE2_LUT_SCHEMA
                and lut_doc.get("preview_only") is True
                and len(lut_doc.get("cards") or []) == 22
            )
        except json.JSONDecodeError:
            lut_ok = False
    probes["phase2_ritual_lut_json"] = {
        "url": f"{APEX}/data/personadiary_ritual_draw_lut_major22_v1.json",
        "status": lut_fetch.get("status"),
        "ok": lut_ok,
    }

    bloom_fetch = _fetch(f"{APEX}/data/personadiary_lattice_convergence_bloom_slice_v1.json")
    bloom_ok = False
    if bloom_fetch.get("ok") and bloom_fetch.get("status") == 200:
        try:
            bloom_doc = json.loads(bloom_fetch["text"])
            bloom_ok = (
                bloom_doc.get("schema") == PHASE2_BLOOM_SCHEMA
                and bloom_doc.get("research_only") is True
                and bloom_doc.get("non_gating") is True
                and any(n.get("kind") == "query" for n in bloom_doc.get("nodes") or [])
            )
        except json.JSONDecodeError:
            bloom_ok = False
    probes["phase2_lattice_bloom_json"] = {
        "url": f"{APEX}/data/personadiary_lattice_convergence_bloom_slice_v1.json",
        "status": bloom_fetch.get("status"),
        "ok": bloom_ok,
    }

    guide = _fetch(f"{APEX}/api/personadiary/daily-guide")
    guide_ok = False
    if guide.get("ok") and guide.get("status") == 200:
        try:
            gj = json.loads(guide["text"])
            guide_ok = gj.get("ok") is True and gj.get("preview_only") is True
        except json.JSONDecodeError:
            guide_ok = False
    probes["daily_guide_api"] = {
        "url": f"{APEX}/api/personadiary/daily-guide",
        "status": guide.get("status"),
        "ok": guide_ok,
    }

    forbidden_scan = pd_copy.scan_text_for_forbidden(ops_text)
    contract = pd_copy.load_copy_contract()
    marker_list = contract.get("smoke_html_markers") or [
        "pd-non-prediction-contract",
        "정신적 방화벽",
        "SEND_GATE: HOLD",
    ]
    missing_contract_markers = [m for m in marker_list if m not in ops_text]
    probes["non_prediction_copy"] = {
        "url": f"{APEX}/ops",
        "forbidden_scan_ok": forbidden_scan["ok"],
        "violations": forbidden_scan["violations"],
        "contract_markers_ok": len(missing_contract_markers) == 0,
        "missing_markers": missing_contract_markers,
        "ok": forbidden_scan["ok"] and len(missing_contract_markers) == 0,
        "detail": (
            "forbidden scan + contract markers pass"
            if forbidden_scan["ok"] and not missing_contract_markers
            else (
                f"violations: {', '.join(forbidden_scan['violations'])}"
                if not forbidden_scan["ok"]
                else f"missing markers: {', '.join(missing_contract_markers)}"
            )
        ),
    }

    moment = _fetch(
        f"{APEX}/api/personadiary/moment",
        method="POST",
        body={"text": "오늘 점심 뭐 먹을까?"},
    )
    moment_ok = False
    intent = None
    card_count = 0
    poi_hint_ok = False
    acode_summary_ok = False
    acode_persona_ok = False
    moment_polish_applied = False
    moment_polish_backend = None
    if moment.get("ok") and moment.get("status") == 200:
        try:
            mj = json.loads(moment["text"])
            m = mj.get("moment") or {}
            intent = m.get("intent")
            card_count = len(m.get("cards") or [])
            moment_ok = mj.get("ok") is True and intent == "meal" and card_count >= 1
            summary = str(m.get("summary_ko") or "")
            acode_summary_ok = "AC-" in summary
            acode = m.get("acode_persona") or {}
            acode_persona_ok = (
                acode.get("schema") == "personadiary_acode_persona_v1"
                and str(acode.get("public_code", "")).startswith("AC-")
            )
            moment_polish_applied = bool(m.get("summary_ko_polished"))
            moment_polish_backend = (m.get("polish_meta") or {}).get("backend")
            poi_hint_ok = any(k in summary for k in ("국물", "곰탕", "메뉴", "찌개", "—"))
            meal_menu_ok = "역" not in summary and "골목" not in summary
            poi_hint_ok = poi_hint_ok and meal_menu_ok
        except json.JSONDecodeError:
            moment_ok = False
            poi_hint_ok = False
            acode_summary_ok = False
            acode_persona_ok = False
    else:
        poi_hint_ok = False
        acode_summary_ok = False
        acode_persona_ok = False
    probes["moment_api"] = {
        "url": f"{APEX}/api/personadiary/moment",
        "status": moment.get("status"),
        "intent": intent,
        "card_count": card_count,
        "poi_hint_ok": poi_hint_ok,
        "acode_summary_ok": acode_summary_ok,
        "acode_persona_ok": acode_persona_ok,
        "moment_polish_applied": moment_polish_applied,
        "moment_polish_backend": moment_polish_backend,
        "ok": moment_ok and poi_hint_ok and acode_summary_ok and acode_persona_ok,
    }

    smoke = {
        "schema": "personadiary_live_ops_smoke_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "apex": APEX,
        "probes": probes,
        "ok": all(p.get("ok") for p in probes.values()),
        "lane": "research_only",
        "hypothesis_tier": "B",
    }
    smoke_path = ROOT / "reports" / "personadiary_live_ops_smoke_latest.json"
    smoke_path.parent.mkdir(parents=True, exist_ok=True)
    smoke_path.write_text(json.dumps(smoke, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    probe_report = ROOT / "reports" / "personadiary_cloudflare_token_probe_latest.json"
    token_meta = {}
    if probe_report.is_file():
        try:
            token_meta = json.loads(probe_report.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            token_meta = {}

    ops = {
        "schema": "personadiary_operational_status_v1",
        "generated_at_utc": smoke["generated_at_utc"],
        "operational_verdict": (
            "DONE for preview — live smoke passed"
            if smoke["ok"]
            else "DEGRADED — see personadiary_live_ops_smoke_latest.json"
        ),
        "live_http": {
            "https://personadiary.com/": {
                "status": probes["apex_page"].get("status"),
                "ok": probes["apex_page"].get("ok"),
            },
            "https://personadiary.com/ops": {
                "status": probes["mobile_ops_page"].get("status"),
                "ok": probes["mobile_ops_page"].get("ok"),
            },
        },
        "api_probe": {
            "daily_guide_ok": probes["daily_guide_api"].get("ok"),
            "moment_ok": probes["moment_api"].get("ok"),
            "moment_intent": probes["moment_api"].get("intent"),
            "cloudflare_token_probe": token_meta.get("token_source"),
            "dns_list_ok": (token_meta.get("dns_list") or {}).get("ok"),
        },
        "mkm_personadiary_dns_token": {
            "env_set": bool(token_meta.get("token_source", "").startswith("MKM_CLOUDFLARE")),
            "required_for_preview": False,
            "required_only_if": "re-running automated DNS ensure/patch via API without dashboard",
        },
        "ssot": "docs/final/artifacts/personadiary_preview_ops_v1_latest.json",
        "smoke_report": str(smoke_path.relative_to(ROOT)).replace("\\", "/"),
    }
    ops_path = ROOT / "reports" / "personadiary_operational_status_latest.json"
    ops_path.write_text(json.dumps(ops, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(smoke, ensure_ascii=False, indent=2))
    print(f"WROTE: {smoke_path}")
    print(f"WROTE: {ops_path}")
    return 0 if smoke["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
