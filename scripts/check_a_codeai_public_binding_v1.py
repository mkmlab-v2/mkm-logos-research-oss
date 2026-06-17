#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "docs" / "final" / "artifacts"
OUT_DEFAULT = ART / "a_codeai_public_binding_check_latest.json"
REPO_PAYLOAD_DEFAULT = ART / "a_codeai_public_copy_web_payload_latest.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _fetch_text(url: str, timeout: float) -> tuple[bool, str]:
    req = Request(
        url,
        headers={
            "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
            "User-Agent": "Mozilla/5.0 (compatible; MKM-AcodeaiBindingCheck/1.0)",
        },
    )
    try:
        with urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return True, body
    except (HTTPError, URLError, TimeoutError, ValueError):
        return False, ""


def _contains_all(text: str, needles: list[str]) -> tuple[bool, list[str]]:
    missing = [needle for needle in needles if needle not in text]
    return len(missing) == 0, missing


def _check_payload_contract(payload_body: str) -> tuple[bool, dict[str, Any]]:
    details: dict[str, Any] = {
        "json_parse_ok": False,
        "schema_ok": False,
        "contract_ok": False,
        "contract_variant": None,
        "reason": "invalid_json",
    }
    try:
        doc = json.loads(payload_body)
    except Exception:
        return False, details
    details["json_parse_ok"] = True
    schema_ok = str(doc.get("schema")) == "a_codeai_public_copy_web_payload_v1"
    details["schema_ok"] = schema_ok
    if not schema_ok:
        details["reason"] = "schema_mismatch"
        return False, details

    # Accept either legacy top-level format or newer sectioned format.
    has_legacy = isinstance(doc.get("commercial_readiness"), dict)
    sections = doc.get("sections", {})
    hero = sections.get("hero", {}) if isinstance(sections, dict) else {}
    has_sectioned = isinstance(sections, dict) and isinstance(hero, dict) and bool(hero.get("title"))
    if has_legacy:
        details["contract_ok"] = True
        details["contract_variant"] = "legacy_top_level"
        details["reason"] = "ok"
        return True, details
    if has_sectioned:
        details["contract_ok"] = True
        details["contract_variant"] = "sectioned_v1"
        details["reason"] = "ok"
        return True, details
    details["reason"] = "payload_contract_missing_required_fields"
    return False, details


def _parse_payload_doc(body: str) -> dict[str, Any] | None:
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return None


def _hero_title(doc: dict[str, Any] | None) -> str:
    if not doc:
        return ""
    sections = doc.get("sections", {})
    if isinstance(sections, dict):
        hero = sections.get("hero", {})
        if isinstance(hero, dict):
            return str(hero.get("title", "")).strip()
    return ""


def _static_h1(html: str) -> str:
    m = re.search(r'id="pg-hero-title"[^>]*>([^<]+)<', html)
    return m.group(1).strip() if m else ""


def _check_content_parity(
    *,
    repo_doc: dict[str, Any] | None,
    live_doc: dict[str, Any] | None,
    home_html: str,
    ko_html: str,
) -> tuple[bool, dict[str, Any]]:
    expected_title = _hero_title(repo_doc)
    live_title = _hero_title(live_doc)
    home_h1 = _static_h1(home_html)
    ko_h1 = _static_h1(ko_html)
    send_gate = str((live_doc or {}).get("meta", {}).get("send_gate", "")).upper()
    status_line = str(((live_doc or {}).get("sections") or {}).get("hero", {}).get("status_line", ""))
    hold_ok = send_gate == "HOLD" or "SEND_GATE=HOLD" in status_line.upper()
    forbidden = ["PointerGuard Router", "Macro Risk Early Warning", "거시 리스크 조기경보"]
    forbidden_hits = [x for x in forbidden if x in home_html or x in ko_html or x in live_title]

    checks = {
        "repo_payload_present": bool(repo_doc),
        "live_payload_present": bool(live_doc),
        "hero_title_repo_vs_live_ok": bool(expected_title and expected_title == live_title),
        "hero_title_static_home_ok": bool(expected_title and expected_title == home_h1),
        "hero_title_static_ko_present_ok": bool(ko_h1 and ("Open Bench" in ko_h1 or "대기명단" in ko_h1)),
        "send_gate_hold_ok": hold_ok,
        "forbidden_legacy_copy_absent_ok": len(forbidden_hits) == 0,
        "operator_footer_ok": "628-86-01742" in home_html and "628-86-01742" in ko_html,
        "expected_title": expected_title,
        "live_title": live_title,
        "home_h1": home_h1,
        "ko_h1": ko_h1,
        "forbidden_hits": forbidden_hits,
    }
    ok = all(
        checks[k]
        for k in (
            "repo_payload_present",
            "live_payload_present",
            "hero_title_repo_vs_live_ok",
            "hero_title_static_home_ok",
            "hero_title_static_ko_present_ok",
            "send_gate_hold_ok",
            "forbidden_legacy_copy_absent_ok",
            "operator_footer_ok",
        )
    )
    return ok, checks


def _check_pilot_narrative(*, pilot_en: str, pilot_ko: str) -> tuple[bool, dict[str, Any]]:
    forbidden = [
        "treasury",
        "risk monitoring",
        "Macro Risk",
        "거시",
        "리스크 모니터링",
        "재무/리스크",
    ]
    forbidden_hits = [x for x in forbidden if x in pilot_en or x in pilot_ko]
    checks = {
        "pilot_en_reachable": bool(pilot_en),
        "pilot_ko_reachable": bool(pilot_ko),
        "enterprise_apply_en_ok": "app.jema-ai.com/enterprise/apply" in pilot_en,
        "enterprise_apply_ko_ok": "app.jema-ai.com/enterprise/apply" in pilot_ko,
        "operator_footer_en_ok": "628-86-01742" in pilot_en,
        "operator_footer_ko_ok": "628-86-01742" in pilot_ko,
        "forbidden_legacy_copy_absent_ok": len(forbidden_hits) == 0,
        "forbidden_hits": forbidden_hits,
    }
    ok = all(
        checks[k]
        for k in (
            "pilot_en_reachable",
            "pilot_ko_reachable",
            "enterprise_apply_en_ok",
            "enterprise_apply_ko_ok",
            "operator_footer_en_ok",
            "operator_footer_ko_ok",
            "forbidden_legacy_copy_absent_ok",
        )
    )
    return ok, checks


def _check_legal_page(*, legal_en: str, legal_ko: str) -> tuple[bool, dict[str, Any]]:
    checks = {
        "legal_en_reachable": bool(legal_en),
        "legal_ko_reachable": bool(legal_ko),
        "operator_en_ok": "628-86-01742" in legal_en and "Moksori Network" in legal_en,
        "operator_ko_ok": "628-86-01742" in legal_ko and "목소리네트워크" in legal_ko,
        "privacy_link_ok": "jema-ai.com/privacy" in legal_en and "jema-ai.com/privacy" in legal_ko,
        "send_gate_hold_mentioned_ok": "HOLD" in legal_en and "HOLD" in legal_ko,
    }
    ok = all(checks.values())
    return ok, checks


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base-url", default="https://a-codeai.com")
    ap.add_argument("--timeout-sec", type=float, default=10.0)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--repo-payload", type=Path, default=REPO_PAYLOAD_DEFAULT)
    args = ap.parse_args()

    base_url = args.base_url.rstrip("/")
    home_url = f"{base_url}/"
    ko_url = f"{base_url}/ko/"
    pilot_url = f"{base_url}/pilot/"
    pilot_ko_url = f"{base_url}/ko/pilot/"
    legal_url = f"{base_url}/legal/"
    legal_ko_url = f"{base_url}/ko/legal/"
    payload_url = f"{base_url}/a_codeai_public_copy_web_payload_latest.json"

    page_markers = [
        "a_codeai_public_copy_web_payload_latest.json",
        "pg-hero-title",
        "pg-status-line",
    ]

    home_ok, home_body = _fetch_text(home_url, timeout=args.timeout_sec)
    ko_ok, ko_body = _fetch_text(ko_url, timeout=args.timeout_sec)
    pilot_ok, pilot_body = _fetch_text(pilot_url, timeout=args.timeout_sec)
    pilot_ko_ok, pilot_ko_body = _fetch_text(pilot_ko_url, timeout=args.timeout_sec)
    legal_ok, legal_body = _fetch_text(legal_url, timeout=args.timeout_sec)
    legal_ko_ok, legal_ko_body = _fetch_text(legal_ko_url, timeout=args.timeout_sec)
    payload_ok, payload_body = _fetch_text(payload_url, timeout=args.timeout_sec)

    home_markers_ok, home_missing = _contains_all(home_body, page_markers)
    ko_markers_ok, ko_missing = _contains_all(ko_body, page_markers)
    payload_contract_ok, payload_contract_details = _check_payload_contract(payload_body) if payload_ok else (False, {"reason": "payload_unreachable"})

    repo_path = args.repo_payload if args.repo_payload.is_absolute() else ROOT / args.repo_payload
    repo_doc = None
    if repo_path.is_file():
        repo_doc = _parse_payload_doc(repo_path.read_text(encoding="utf-8"))
    live_doc = _parse_payload_doc(payload_body) if payload_ok else None
    content_ok, content_details = _check_content_parity(
        repo_doc=repo_doc,
        live_doc=live_doc,
        home_html=home_body if home_ok else "",
        ko_html=ko_body if ko_ok else "",
    )
    pilot_ok_check, pilot_details = _check_pilot_narrative(
        pilot_en=pilot_body if pilot_ok else "",
        pilot_ko=pilot_ko_body if pilot_ko_ok else "",
    )
    legal_ok_check, legal_details = _check_legal_page(
        legal_en=legal_body if legal_ok else "",
        legal_ko=legal_ko_body if legal_ko_ok else "",
    )

    all_ok = bool(
        home_ok
        and ko_ok
        and pilot_ok
        and pilot_ko_ok
        and legal_ok
        and legal_ko_ok
        and payload_ok
        and home_markers_ok
        and ko_markers_ok
        and payload_contract_ok
        and content_ok
        and pilot_ok_check
        and legal_ok_check
    )
    decision = "PASS" if all_ok else "FAIL"

    out_doc: dict[str, Any] = {
        "schema": "a_codeai_public_binding_check_v1",
        "generated_at_utc": _now_utc(),
        "target": {
            "base_url": base_url,
            "home_url": home_url,
            "ko_url": ko_url,
            "pilot_url": pilot_url,
            "pilot_ko_url": pilot_ko_url,
            "legal_url": legal_url,
            "legal_ko_url": legal_ko_url,
            "payload_url": payload_url,
        },
        "all_ok": all_ok,
        "decision": decision,
        "checks": {
            "home": {
                "reachable": home_ok,
                "markers_ok": home_markers_ok,
                "missing_markers": home_missing,
            },
            "ko": {
                "reachable": ko_ok,
                "markers_ok": ko_markers_ok,
                "missing_markers": ko_missing,
            },
            "payload": {
                "reachable": payload_ok,
                "contract_ok": payload_contract_ok,
                "contract_details": payload_contract_details,
            },
            "content_parity": {
                "ok": content_ok,
                "details": content_details,
            },
            "pilot_narrative": {
                "ok": pilot_ok_check,
                "details": pilot_details,
            },
            "legal_page": {
                "ok": legal_ok_check,
                "details": legal_details,
            },
        },
        "notes": [
            "FAIL means payload is not fully wired into the published landing HTML yet.",
            "Use this check after deploy to prove runtime binding is active on both '/' and '/ko/'.",
            "content_parity compares live payload/static H1 against repo SSOT artifact.",
        ],
    }

    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "all_ok": all_ok, "decision": decision}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
