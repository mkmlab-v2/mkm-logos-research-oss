#!/usr/bin/env python3
"""Assemble PersonaDiary daily response package from commander_daily_fortune v1_1.

Product concept SSOT: docs/final/artifacts/PERSONADIARY_DAILY_RESPONSE_PACKAGE_V1_CONTRACT.json
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FORTUNE = ROOT / "reports" / "commander_daily_fortune_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "personadiary_daily_response_package_v1_latest.json"
PUBLIC_MIRROR = (
    ROOT / "projects" / "no1kmedi" / "public" / "data" / "personadiary_daily_response_package_v1.json"
)
CONCEPT_KO = (
    "오늘의 마음 일기 — 명리·4AI·라이프·성경 앵커·찰나의 나라(뉴스·코스피·거시) 융합 가이드"
)
DISCLAIMER_KO = (
    "[가설]·[NON_GATING] 마음돌봄·리플렉션 전용. "
    "임상·처방·투자·시장 예언·실매매 확정 아님. "
    "저장·결제·Track A 합선 없음."
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _section_id_from_header(line: str) -> Optional[str]:
    if "개인 일운 (명리)" in line:
        return "myeongni"
    if "개인 일운 (MKM 4AI)" in line:
        return "mkm_4ai"
    if "오늘 라이프" in line:
        return "lifestyle"
    if "성경 앵커" in line:
        return "logos_anchor"
    if "찰나의 나라" in line or "세상×나" in line:
        return "world_pulse"
    if "초론 스트림" in line or "오늘 초론" in line:
        return "hypothesis_stream"
    if "컨디션·바이어스" in line or "컨디션" in line and "틸트" in line:
        return "user_condition"
    return None


def _parse_telegram_sections(lines: List[str]) -> List[Dict[str, Any]]:
    titles = {
        "myeongni": "오늘의 팔자 (명리)",
        "mkm_4ai": "마음 에너지 (MKM 4AI)",
        "lifestyle": "오늘의 라이프",
        "logos_anchor": "오늘의 성경 앵커",
        "world_pulse": "찰나의 나라 (세상×나)",
        "hypothesis_stream": "오늘 초론 스트림",
        "user_condition": "컨디션·바이어스 틸트",
    }
    sections: Dict[str, List[str]] = {k: [] for k in titles}
    current: Optional[str] = None
    for raw in lines:
        ln = raw.strip()
        if not ln:
            continue
        sid = _section_id_from_header(ln)
        if sid:
            current = sid
            continue
        if current:
            body = ln.lstrip()
            if body.startswith("▸"):
                body = body[1:].strip()
            sections[current].append(body)
    out: List[Dict[str, Any]] = []
    for sid, title in titles.items():
        if sections[sid]:
            out.append({"id": sid, "title_ko": title, "lines": sections[sid]})
    return out


def _first_line(sections: List[Dict[str, Any]], sid: str) -> str:
    for sec in sections:
        if sec.get("id") == sid and sec.get("lines"):
            return str(sec["lines"][0])
    return ""


def _build_news_me_hypo_block(
    sections: List[Dict[str, Any]],
    fortune: Dict[str, Any],
    hypo_meta: Dict[str, Any],
    world_meta: Dict[str, Any],
) -> Dict[str, Any] | None:
    """Dedicated 「오늘의 뉴스 × 나 [HYPO]」 card — mkmlife upstream chain surface."""
    world_lines = next((s for s in sections if s["id"] == "world_pulse"), {}).get("lines") or []
    fusion_line = str(world_meta.get("fusion_one_liner_ko") or "").strip()
    synthesis = str(hypo_meta.get("synthesis_ko") or "").strip()
    world_body = "\n".join(world_lines[:4]).strip()
    body_parts: List[str] = []
    if fusion_line:
        body_parts.append(fusion_line)
    elif world_body:
        body_parts.append(world_body[:280])
    if synthesis:
        body_parts.append(synthesis[:280])
    if not body_parts:
        return None
    branches = hypo_meta.get("branches") or []
    mkmlife_href = "https://mkmlife.com/oracle-sphere"
    out: Dict[str, Any] = {
        "type": "news_me_hypo",
        "title_ko": "오늘의 뉴스 × 나",
        "body_ko": "\n\n".join(body_parts)[:600],
        "badge_ko": "[HYPO][NON_GATING]",
        "mkmlife_href": mkmlife_href,
    }
    if branches:
        out["branches"] = branches[:5]
    return out


def _build_ui_blocks(
    sections: List[Dict[str, Any]],
    fortune: Dict[str, Any],
    *,
    calendar_kst: str,
    city: str,
) -> List[Dict[str, Any]]:
    myeongni = _first_line(sections, "myeongni")
    lifestyle = next((s for s in sections if s["id"] == "lifestyle"), {"lines": []})
    logos = next((s for s in sections if s["id"] == "logos_anchor"), {"lines": []})
    world = next((s for s in sections if s["id"] == "world_pulse"), {"lines": []})
    anchor = fortune.get("logos_daily_anchor") or {}
    golden = anchor.get("golden_anchor") or {}
    world_meta = fortune.get("world_pulse_fusion") or {}
    hypo_meta = fortune.get("hypothesis_stream") or {}
    cond_meta = fortune.get("user_condition") or {}
    tilt_ko = str((cond_meta.get("advisory_investment_bias_tilt") or {}).get("tilt_ko") or "")
    fusion_line = str(world_meta.get("fusion_one_liner_ko") or "").strip()
    synthesis = str(hypo_meta.get("synthesis_ko") or "").strip()
    hero_body = fusion_line or myeongni or "명리 일운을 불러오는 중입니다."
    if synthesis and synthesis not in hero_body:
        hero_body = f"{synthesis}\n\n{hero_body}"
    if myeongni and fusion_line and myeongni not in hero_body:
        hero_body = f"{fusion_line}\n\n{myeongni}"

    blocks: List[Dict[str, Any]] = [
        {
            "type": "hero",
            "title_ko": f"찰나의 나라 · {calendar_kst}",
            "body_ko": hero_body[:500],
            "badge_ko": f"{city} · 세상×나 · [가설]",
        }
    ]
    news_me = _build_news_me_hypo_block(sections, fortune, hypo_meta, world_meta)
    if news_me:
        blocks.append(news_me)
    for sec in sections:
        if sec["id"] == "logos_anchor":
            continue
        block_type = "card"
        if sec["id"] == "world_pulse":
            block_type = "world_pulse"
        elif sec["id"] == "hypothesis_stream":
            block_type = "hypothesis_stream"
        elif sec["id"] == "user_condition":
            block_type = "user_condition"
        blk: Dict[str, Any] = {
            "type": block_type,
            "title_ko": sec["title_ko"],
            "body_ko": "\n".join(sec.get("lines") or [])[:600],
        }
        if sec["id"] in ("world_pulse", "hypothesis_stream", "user_condition"):
            blk["badge_ko"] = "[NON_GATING][가설]"
        if sec["id"] == "hypothesis_stream" and hypo_meta.get("branches"):
            blk["branches"] = hypo_meta.get("branches")[:5]
        if sec["id"] == "user_condition" and tilt_ko:
            blk["tilt_ko"] = tilt_ko[:200]
        blocks.append(blk)
    if golden.get("ref") or logos.get("lines"):
        verse_body = ""
        for ln in logos.get("lines") or []:
            if "앵커:" in ln:
                verse_body = ln.replace("앵커:", "").strip()
                break
        blocks.append(
            {
                "type": "verse",
                "title_ko": "오늘의 성경 앵커",
                "ref": str(golden.get("ref") or "—"),
                "body_ko": verse_body or str(golden.get("text") or "")[:200],
                "badge_ko": "[NON_GATING][가설]",
            }
        )
    blocks.append({"type": "disclaimer", "title_ko": "안내", "body_ko": DISCLAIMER_KO})
    return blocks


def _reflect_template(sections: List[Dict[str, Any]], user_snippet: str = "{user}") -> str:
    myeongni = _first_line(sections, "myeongni")
    life = _first_line(sections, "lifestyle")
    world = _first_line(sections, "world_pulse")
    if not world:
        for ln in next((s for s in sections if s["id"] == "world_pulse"), {}).get("lines") or []:
            if "융합 한 줄" in ln:
                world = ln.replace("융합 한 줄:", "").strip()[:100]
                break
    logos_lines = next((s for s in sections if s["id"] == "logos_anchor"), {}).get("lines") or []
    verse = ""
    for ln in logos_lines:
        if "앵커:" in ln:
            verse = ln.replace("앵커:", "").strip()[:80]
            break
    parts = [
        f"오늘 당신이 남긴 마음: \"{user_snippet}\"",
        f"명리 한 줄: {myeongni[:100]}" if myeongni else "",
        f"찰나의 판: {world[:100]}" if world else "",
        f"라이프: {life[:80]}" if life else "",
        f"성경 앵커: {verse}" if verse else "",
        "구슬은 가이드형 성찰만 비춥니다. 저장·임상·투자 판정과 무관합니다.",
    ]
    return " ".join(p for p in parts if p)


def assemble_package(
    fortune: Dict[str, Any],
    *,
    fortune_path: Path,
) -> Dict[str, Any]:
    schema = fortune.get("schema") or ""
    if schema not in ("commander_daily_fortune_v1", "commander_daily_fortune_v1_1"):
        raise ValueError(f"unsupported fortune schema: {schema}")

    tg_lines = list(fortune.get("telegram_append_lines") or [])
    # drop duplicate header if present in telegram (personal digest adds its own)
    filtered = [ln for ln in tg_lines if not ln.startswith("지휘관 오늘 일운 ·")]
    sections = _parse_telegram_sections(filtered)
    calendar_kst = str(fortune.get("calendar_kst") or "")
    city = str(fortune.get("city_default") or "Seoul")
    ui_blocks = _build_ui_blocks(sections, fortune, calendar_kst=calendar_kst, city=city)
    telegram_text = "\n".join(filtered).strip()

    profile_id = fortune.get("profile_id") or os.environ.get("MKM_PERSONADIARY_PROFILE_ID") or "commander"

    return {
        "schema": "personadiary_daily_response_package_v1",
        "profile_id": profile_id,
        "product": "personadiary.com",
        "hypothesis_tier": "B",
        "non_gating": True,
        "boundary_ack": True,
        "concept_ko": CONCEPT_KO,
        "disclaimer_ko": DISCLAIMER_KO,
        "generated_at_utc": _utc_now(),
        "calendar_kst": calendar_kst,
        "city_default": city,
        "source_fortune_path": str(fortune_path),
        "contract_path": "docs/final/artifacts/PERSONADIARY_DAILY_RESPONSE_PACKAGE_V1_CONTRACT.json",
        "sections": sections,
        "ui_blocks": ui_blocks,
        "reflect_template_ko": _reflect_template(sections),
        "telegram_text": telegram_text,
        "upstream": {
            "lifestyle": fortune.get("lifestyle_concierge"),
            "logos_anchor": fortune.get("logos_daily_anchor"),
            "world_pulse_fusion": fortune.get("world_pulse_fusion"),
            "hypothesis_stream": fortune.get("hypothesis_stream"),
            "kernel_skins_ref": "docs/final/artifacts/mkm_life_anchor_os_kernel_skins_v1_latest.json",
            "mkmlife_chain_env": "MKM_SYNC_MKMLIFE_ONE_QUESTION_CONTEXT",
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fortune-json", type=Path, default=DEFAULT_FORTUNE)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--sync-public",
        action="store_true",
        help="Mirror JSON to projects/no1kmedi/public/data/ for Next.js",
    )
    ap.add_argument("--stdout-only", action="store_true")
    args = ap.parse_args()

    fortune = _read_json(args.fortune_json)
    if not fortune:
        raise SystemExit(f"missing fortune: {args.fortune_json}")

    payload = assemble_package(fortune, fortune_path=args.fortune_json)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if args.sync_public:
        PUBLIC_MIRROR.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(args.out_json, PUBLIC_MIRROR)

    if args.stdout_only:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"WROTE: {args.out_json}")
        if args.sync_public:
            print(f"MIRROR: {PUBLIC_MIRROR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
