#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "docs" / "final" / "artifacts"
OUT_DEFAULT = ART / "a_codeai_public_binding_check_latest.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _fetch_text(url: str, timeout: float) -> tuple[bool, str]:
    try:
        with urlopen(url, timeout=timeout) as resp:
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


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base-url", default="https://a-codeai.com")
    ap.add_argument("--timeout-sec", type=float, default=10.0)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    base_url = args.base_url.rstrip("/")
    home_url = f"{base_url}/"
    ko_url = f"{base_url}/ko/"
    payload_url = f"{base_url}/a_codeai_public_copy_web_payload_latest.json"

    page_markers = [
        "a_codeai_public_copy_web_payload_latest.json",
        "pg-hero-title",
        "pg-status-line",
    ]

    home_ok, home_body = _fetch_text(home_url, timeout=args.timeout_sec)
    ko_ok, ko_body = _fetch_text(ko_url, timeout=args.timeout_sec)
    payload_ok, payload_body = _fetch_text(payload_url, timeout=args.timeout_sec)

    home_markers_ok, home_missing = _contains_all(home_body, page_markers)
    ko_markers_ok, ko_missing = _contains_all(ko_body, page_markers)
    payload_contract_ok, payload_contract_details = _check_payload_contract(payload_body) if payload_ok else (False, {"reason": "payload_unreachable"})

    all_ok = bool(home_ok and ko_ok and payload_ok and home_markers_ok and ko_markers_ok and payload_contract_ok)
    decision = "PASS" if all_ok else "FAIL"

    out_doc: dict[str, Any] = {
        "schema": "a_codeai_public_binding_check_v1",
        "generated_at_utc": _now_utc(),
        "target": {
            "base_url": base_url,
            "home_url": home_url,
            "ko_url": ko_url,
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
        },
        "notes": [
            "FAIL means payload is not fully wired into the published landing HTML yet.",
            "Use this check after deploy to prove runtime binding is active on both '/' and '/ko/'.",
        ],
    }

    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "all_ok": all_ok, "decision": decision}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
