#!/usr/bin/env python3
"""PersonaDiary live ops smoke — apex + moment API (Phase B). Writes JSON reports."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UA = "MKM-PersonadiarySmoke/1.0"
APEX = "https://personadiary.com"

HUB_FOOTER_MARKERS = (
    "pd-hub-footer",
    "MKM 관련 제품",
    "JEMA AI 브랜드",
    "mkmlife.com",
)
HUB_FOOTER_BOUNDARY = "합치지 않습니다"

PHASE2_HTML_MARKERS = (
    "pd-ritual-draw",
    "Lattice Convergence",
    "빛의 구슬",
)
PHASE2_LUT_SCHEMA = "personadiary_ritual_draw_lut_major22_v1"
PHASE2_BLOOM_SCHEMA = "magic_orb_graph_bloom_v1"


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

    moment = _fetch(
        f"{APEX}/api/personadiary/moment",
        method="POST",
        body={"text": "오늘 점심 뭐 먹을까?"},
    )
    moment_ok = False
    intent = None
    card_count = 0
    if moment.get("ok") and moment.get("status") == 200:
        try:
            mj = json.loads(moment["text"])
            m = mj.get("moment") or {}
            intent = m.get("intent")
            card_count = len(m.get("cards") or [])
            moment_ok = mj.get("ok") is True and intent == "meal" and card_count >= 1
        except json.JSONDecodeError:
            moment_ok = False
    probes["moment_api"] = {
        "url": f"{APEX}/api/personadiary/moment",
        "status": moment.get("status"),
        "intent": intent,
        "card_count": card_count,
        "ok": moment_ok,
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
