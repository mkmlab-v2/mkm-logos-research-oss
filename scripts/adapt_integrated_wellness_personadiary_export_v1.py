#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Adapt IWS v2 personadiary render → personadiary_daily_response_package_v1 ui_blocks."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _calendar_kst() -> str:
    return datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d")


def _myeongni_one_liner(resolved_doc: dict[str, Any] | None) -> tuple[str, str] | None:
    if not resolved_doc:
        return None
    for node in resolved_doc.get("resolved_evidence_stream") or []:
        if node.get("node_id") != "myeongni_temporal_stub":
            continue
        payload = node.get("content_payload") or {}
        title = (payload.get("title") or "명리 시간축").strip()
        body = (payload.get("body") or "").strip()
        if not body:
            return None
        first_line = body.split("\n", 1)[0].strip()
        if len(first_line) > 220:
            first_line = first_line[:217] + "…"
        return title, first_line
    return None


def adapt(render_doc: dict[str, Any], resolved_doc: dict[str, Any] | None = None) -> dict[str, Any]:
    ui_blocks_raw = render_doc.get("ui_blocks") or []
    lex = (resolved_doc or {}).get("lexicon_profile") or {}
    consumer = lex.get("consumer_a_code") or {}
    chief = (resolved_doc or {}).get("chief_concern") or {}

    hero_title = consumer.get("display_name_ko") or "오늘의 리듬"
    hero_body = consumer.get("tagline_ko") or render_doc.get("disclaimer", "")

    blocks: list[dict[str, Any]] = [
        {
            "type": "hero",
            "title_ko": f"A-Code · {hero_title}",
            "body_ko": hero_body,
            "badge_ko": consumer.get("code_id", ""),
            "evidence_tier": "coaching_heuristic",
        }
    ]

    myeongni = _myeongni_one_liner(resolved_doc)
    if myeongni:
        title_ko, body_ko = myeongni
        blocks.append(
            {
                "type": "card",
                "title_ko": f"몸·리듬 — 흐름 참고 · {title_ko}",
                "body_ko": body_ko,
                "badge_ko": "[가설][NON_GATING]",
                "evidence_tier": "coaching_heuristic",
            }
        )

    for raw in ui_blocks_raw:
        btype = raw.get("block_type") or raw.get("type")
        if btype == "action_card_list":
            for item in raw.get("items") or []:
                blocks.append(
                    {
                        "type": "card",
                        "title_ko": f"몸·리듬 — {item.get('title', '')}",
                        "body_ko": item.get("body", ""),
                        "badge_ko": "[가설][웰니스]",
                        "evidence_tier": "coaching_heuristic",
                    }
                )
        elif btype == "breath_practice":
            for item in raw.get("items") or []:
                blocks.append(
                    {
                        "type": "card",
                        "title_ko": f"몸·리듬 — 호흡·코어 · {item.get('title', '')}",
                        "body_ko": item.get("body", ""),
                        "badge_ko": "[가설][웰니스]",
                        "evidence_tier": "literature_supported",
                    }
                )

    lifestyle_lines = []
    if chief.get("title_ko"):
        lifestyle_lines.append(f"주제: {chief['title_ko']}")
    for block in blocks:
        if block["type"] == "card":
            lifestyle_lines.append(f"{block['title_ko']}: {block.get('body_ko', '')[:120]}")

    return {
        "schema": "personadiary_daily_response_package_v1",
        "product": "personadiary.com",
        "hypothesis_tier": "B",
        "non_gating": True,
        "boundary_ack": True,
        "concept_ko": "Integrated Wellness v2 — 몸·리듬 카드 [가설]",
        "disclaimer_ko": render_doc.get("disclaimer")
        or "[가설] 마음돌봄·리플렉션 전용. 임상·처방·투자·실매매 확정 아님.",
        "generated_at_utc": _now_utc(),
        "calendar_kst": _calendar_kst(),
        "city_default": "Seoul",
        "source_iws_v2": True,
        "sections": [
            {
                "id": "lifestyle",
                "title_ko": "오늘의 라이프 (IWS v2)",
                "lines": lifestyle_lines or ["IWS v2 웰니스 참고 — 임상 단정 없음"],
            }
        ],
        "ui_blocks": blocks,
        "reflect_template_ko": "오늘 당신이 남긴 마음: \"{user}\" — A-Code 리듬은 참고용입니다.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Adapt IWS personadiary render to daily package")
    parser.add_argument("--render-json", required=True, type=Path)
    parser.add_argument("--resolved-json", type=Path)
    parser.add_argument("--out-json", required=True, type=Path)
    args = parser.parse_args()

    render_doc = json.loads(args.render_json.read_text(encoding="utf-8-sig"))
    resolved_doc = None
    if args.resolved_json and args.resolved_json.is_file():
        resolved_doc = json.loads(args.resolved_json.read_text(encoding="utf-8-sig"))

    pkg = adapt(render_doc, resolved_doc)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(pkg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.out_json), "ui_blocks": len(pkg["ui_blocks"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
