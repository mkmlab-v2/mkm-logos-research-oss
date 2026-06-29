#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render resolved IWS v2 for mkmlife | personadiary | no1kmedi."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.integrated_wellness_solution_v2_core import SASANG_KO, load_json  # noqa: E402

DISCLAIMERS = {
    "tier_a_full": (
        "본 리포트는 B-track 웰니스 참고 자료이며 진단·치료를 대체하지 않습니다. "
        "국소 부위 감량(Spot reduction)은 불가능합니다. [HYPO] 사상·명리 구간은 연구 격리입니다."
    ),
    "tier_b_compact": (
        "일상 카드는 참고용이며 의료 행위가 아닙니다. A-Code는 심리검사가 아닙니다."
    ),
    "clinician_internal_disclaimer": (
        "CDSS 보조 초안 — 한의사 human_confirm 전 임상 확정 금지. "
        "사상·명리는 [HYPO]/[NON_GATING] 참고만."
    ),
}


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _nodes_by_tier(stream: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for node in stream:
        tier = node.get("tier", "FACT")
        out.setdefault(tier, []).append(node)
    return out


def _md_section(title: str, body: str) -> str:
    return f"### {title}\n\n{body}\n"


def render_mkmlife(resolved: dict[str, Any]) -> dict[str, Any]:
    spec = resolved["domain_payload_matrix"]["mkmlife"]
    stream = resolved.get("resolved_evidence_stream") or []
    by_tier = _nodes_by_tier(stream)
    profile = resolved["client_profile"]
    lex = resolved.get("lexicon_profile") or {}
    consumer = lex.get("consumer_a_code") or {}

    sections: list[str] = []
    sections.append(f"# {resolved['chief_concern']['title_ko']}\n")
    if consumer:
        sections.append(
            f"**A-Code:** {consumer.get('code_id')} — {consumer.get('display_name_ko')} "
            f"({consumer.get('tagline_ko')})\n"
        )

    for node in by_tier.get("FACT", []):
        p = node["content_payload"]
        sections.append(_md_section(p["title"], p["body"]))

    for node in by_tier.get("HYPO", []):
        p = node["content_payload"]
        sections.append(_md_section(f"[HYPO] {p['title']}", p["body"]))

    for node in by_tier.get("ACTION", []):
        p = node["content_payload"]
        sections.append(_md_section(f"권장 행동: {p['title']}", p["body"]))

    return {
        "schema": "mkmlife_one_question_report_v1",
        "version": "1.0.0",
        "generated_at_utc": _now_utc(),
        "solution_id": resolved.get("metadata", {}).get("solution_id"),
        "render_target": spec["render_target"],
        "disclaimer": DISCLAIMERS[spec["disclaimer_required"]],
        "client_profile_summary": {
            "age_band": profile.get("computed_age_band"),
            "sasang_consumer_label": consumer.get("display_name_ko"),
            "a_code": profile.get("a_code_consumer"),
        },
        "body_markdown": "\n".join(sections),
        "boundary": resolved.get("boundary_contract"),
    }


def render_personadiary(resolved: dict[str, Any]) -> dict[str, Any]:
    spec = resolved["domain_payload_matrix"]["personadiary"]
    stream = resolved.get("resolved_evidence_stream") or []
    lex = resolved.get("lexicon_profile") or {}
    consumer = lex.get("consumer_a_code") or {}

    action_cards = []
    breath_cards = []
    for node in stream:
        if node.get("tier") not in ("ACTION", "FACT"):
            continue
        tags = set(node.get("action_tags") or [])
        card = {
            "node_id": node["node_id"],
            "title": node["content_payload"]["title"],
            "body": node["content_payload"]["body"],
        }
        if "breath" in tags or "core_static" in tags:
            breath_cards.append(card)
        elif node.get("tier") == "ACTION":
            action_cards.append(card)

    ui_blocks = [
        {
            "block_id": "rhythm_header",
            "block_type": "header",
            "title": consumer.get("display_name_ko") or "오늘의 리듬",
            "subtitle": consumer.get("tagline_ko", ""),
            "a_code": resolved["client_profile"].get("a_code_consumer"),
        },
        {
            "block_id": "action_cards",
            "block_type": "action_card_list",
            "items": action_cards[:6],
        },
        {
            "block_id": "breath_core",
            "block_type": "breath_practice",
            "items": breath_cards[:3],
        },
    ]

    return {
        "schema": "personadiary_daily_response_package_v1",
        "version": "1.0.0",
        "generated_at_utc": _now_utc(),
        "render_target": spec["render_target"],
        "disclaimer": DISCLAIMERS[spec["disclaimer_required"]],
        "ui_blocks": ui_blocks,
        "boundary": resolved.get("boundary_contract"),
    }


def render_no1kmedi(resolved: dict[str, Any]) -> dict[str, Any]:
    spec = resolved["domain_payload_matrix"]["no1kmedi"]
    stream = resolved.get("resolved_evidence_stream") or []
    profile = resolved["client_profile"]
    lex = resolved.get("lexicon_profile") or {}
    native = lex.get("clinician_native") or {}
    sasang = profile.get("sasang_internal", "unknown")

    lines = [
        f"**주소:** {resolved['chief_concern']['title_ko']}",
        f"**체질(사상):** {native.get('sasang_ko', SASANG_KO.get(sasang, ''))} "
        f"({native.get('organ_pair_ko', '')})",
        "",
        "#### 생활지도 초안 (CDSS 보조 — human_confirm 필수)",
        "",
    ]

    for node in stream:
        tier = node.get("tier")
        if tier == "NON_GATING":
            continue
        p = node["content_payload"]
        prefix = ""
        if tier == "HYPO":
            prefix = "[HYPO] "
        elif tier == "FACT":
            prefix = "[FACT] "
        elif tier == "ACTION":
            prefix = "[권장] "
        elif tier == "POLICY":
            prefix = "[정책] "
        lines.append(f"- {prefix}**{p['title']}** — {p['body']}")

    suppressed = resolved.get("suppression_log") or []
    if suppressed:
        lines.append("")
        lines.append("#### 제외된 권고 (suppression_log)")
        for entry in suppressed:
            lines.append(
                f"- ~~{entry['node_id']}~~ ({entry['tier_blocked_by']}): {entry['reason']}"
            )

    lifestyle_md = "\n".join(lines)

    return {
        "schema": "no1kmedi_clinician_lifestyle_draft_v1",
        "version": "1.0.0",
        "generated_at_utc": _now_utc(),
        "render_target": spec["render_target"],
        "human_confirm_required": spec.get("human_confirm_required", True),
        "disclaimer": DISCLAIMERS[spec["disclaimer_required"]],
        "patient_slots": [
            {
                "slot_order": 1,
                "slot_id": "sasang",
                "trust_tier": "clinical_reference",
                "included": True,
                "title": "체질·생활 리듬 (사상의학) — CDSS 초안",
                "body_markdown": lifestyle_md,
                "human_confirm_required": True,
            }
        ],
        "suppression_log_count": len(suppressed),
        "suppression_log": suppressed,
        "boundary": resolved.get("boundary_contract"),
    }


RENDERERS = {
    "mkmlife": render_mkmlife,
    "personadiary": render_personadiary,
    "no1kmedi": render_no1kmedi,
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Render IWS v2 for a domain")
    parser.add_argument("--in-json", required=True, type=Path, help="Resolved SSOT JSON")
    parser.add_argument(
        "--target",
        required=True,
        choices=sorted(RENDERERS.keys()),
        help="Domain renderer",
    )
    parser.add_argument("--out-json", required=True, type=Path)
    args = parser.parse_args()

    resolved = load_json(args.in_json)
    payload = RENDERERS[args.target](resolved)

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(json.dumps({"ok": True, "target": args.target, "out": str(args.out_json)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
