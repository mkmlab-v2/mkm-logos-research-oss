#!/usr/bin/env python3
"""Assemble PersonaDiary moment response from daily package + user query [HYPO].

SSOT input: personadiary_daily_response_package_v1 JSON (disk).
Does not re-run manseryeok, weather, or news pipelines.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from classify_personadiary_moment_intent_v1 import classify_intent
from personadiary_acode_profile_v1 import (
    build_moment_meal_menu_recommendation,
    derive_personadiary_acode_profile,
)
from personadiary_consumer_copy_v1 import (
    build_moment_summary_ko,
    pick_lines_for_intent,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKAGE = ROOT / "docs/final/artifacts/personadiary_daily_response_package_v1_latest.json"

DISCLAIMER_KO = (
    "[가설]·[NON_GATING] 마음돌봄·순간 가이드 전용. "
    "임상·처방·투자·시장 예언·실매매·mkmlife 유료 리포트와 무관. "
    "preview_only · 저장 없음."
)

from personadiary_moment_intent_weights_v1 import (
    intent_keywords,
    intent_priority,
    intent_weights,
    non_gating_sections,
    package_required_sections,
    section_titles,
)

_INTENT_KEYWORDS = intent_keywords()
_PRIORITY = intent_priority()
_INTENT_WEIGHTS = intent_weights()
_SECTION_TITLES = section_titles()
_NON_GATING = set(non_gating_sections())
_PACKAGE_REQUIRED = package_required_sections()

def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _section_map(package: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for sec in package.get("sections") or []:
        if isinstance(sec, dict) and sec.get("id"):
            out[str(sec["id"])] = sec
    return out


def _section_body(sec: dict[str, Any] | None, *, intent: str) -> str:
    if not sec:
        return ""
    lines = [str(ln).strip() for ln in (sec.get("lines") or []) if str(ln).strip()]
    picked = pick_lines_for_intent(lines, intent=intent)
    return "\n".join(picked)[:480]


def assemble_moment_response(
    package: dict[str, Any],
    query: str,
    *,
    classification: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if package.get("schema") != "personadiary_daily_response_package_v1":
        raise ValueError("package schema must be personadiary_daily_response_package_v1")

    clf = classification or classify_intent(query)
    intent = str(clf.get("intent") or "reflect")
    weights = _INTENT_WEIGHTS.get(intent) or _INTENT_WEIGHTS["reflect"]
    sec_map = _section_map(package)

    cards: list[dict[str, Any]] = []
    for sid, weight in sorted(weights.items(), key=lambda x: -x[1]):
        body = _section_body(sec_map.get(sid), intent=intent)
        if not body:
            continue
        card: dict[str, Any] = {
            "section_id": sid,
            "lens": sid,
            "title_ko": _SECTION_TITLES.get(sid, sid),
            "body_ko": body,
            "weight": round(weight, 2),
        }
        if sid in _NON_GATING:
            card["badge_ko"] = "[NON_GATING][가설]"
        else:
            card["badge_ko"] = "[가설]"
        cards.append(card)

    coverage_gaps: list[str] = []
    present_ids = set(sec_map.keys())
    for req_sid in _PACKAGE_REQUIRED.get(intent, []):
        if req_sid not in present_ids:
            coverage_gaps.append(f"missing_required_section:{req_sid}")

    if intent == "meal":
        summary_ko = build_moment_meal_menu_recommendation(package)[:400]
    else:
        summary_ko = build_moment_summary_ko(intent=intent, cards=cards)[:400]

    acode_persona = derive_personadiary_acode_profile(package)

    return {
        "schema": "personadiary_moment_response_v1",
        "product": "personadiary.com",
        "hypothesis_tier": "B",
        "preview_only": True,
        "non_gating": True,
        "prophecy_vote": "none",
        "lane": "research_only",
        "regime_field": "regime_personadiary_moment_exploration",
        "query_text": query.strip()[:500],
        "intent": intent,
        "intent_classification": clf,
        "calendar_kst": package.get("calendar_kst"),
        "city_default": package.get("city_default"),
        "profile_id": package.get("profile_id") or "commander",
        "source_package_schema": package.get("schema"),
        "cards": cards[:4],
        "summary_ko": summary_ko,
        "acode_persona": acode_persona,
        "disclaimer_ko": package.get("disclaimer_ko") or DISCLAIMER_KO,
        "generated_at_utc": _utc_now(),
        "explicit_gaps": [
            "summary_ko is deterministic SSOT; optional summary_ko_polished from package preset cache only.",
            "Live Ollama per-request polish not on VPS — refresh with MKM_PERSONADIARY_MOMENT_OLLAMA_POLISH=1.",
            "No diary persistence — preview_only.",
            "mkmlife payment / Track A auto-merge forbidden.",
            *coverage_gaps,
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--package-json", type=Path, default=DEFAULT_PACKAGE)
    ap.add_argument("--query", required=True)
    ap.add_argument("--out-json", type=Path, default=None)
    args = ap.parse_args()

    package = json.loads(args.package_json.read_text(encoding="utf-8-sig"))
    doc = assemble_moment_response(package, args.query)
    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    if args.out_json:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(payload, encoding="utf-8")
        print(f"WROTE: {args.out_json} intent={doc['intent']}")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
