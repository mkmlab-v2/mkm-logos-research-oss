#!/usr/bin/env python3
"""PCO v0 — keyword/tag routing to 2–3 instincts ([HYPO] · research_only)."""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_CODEBOOK = ROOT / "docs/final/artifacts/prompt_codebook_instincts_v0.json"
DEFAULT_OUT = ROOT / "reports/prompt_codebook_route_v1_latest.json"

TAG_KEYWORDS: dict[str, list[str]] = {
    "crisis": ["죽고", "자해", "끝내고", "목숨"],
    "jailbreak": ["탈옥", "jailbreak", "시스템 프롬프트", "역할 무시", "DAN"],
    "edutech": ["숙제", "시험", "학습", "튜터", "문제"],
    "cs": ["환불", "배송", "고객", "불만", "문의"],
    "wellness": ["기분", "스트레스", "마음", "일기", "휴식", "우울"],
    "cooldown": ["과부하", "지쳤", "너무 힘들", "쉬고 싶"],
    "enterprise": ["감사", "로그", "테넌트", "컴플라이언스"],
    "warmth": ["위로", "따뜻", "격려"],
    "short": ["짧게", "간단히", "요약"],
    "clinical": ["진단", "처방", "약 먹", "약을"],
    "privacy": ["개인정보", "저장해"],
    "dialog": ["주제", "새로 시작", "잊고"],
    "low_intensity": ["자극", "조용", "호흡", "낮은 강도"],
    "logos": ["성경", "투자 타이밍", "구절"],
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _infer_tags(text: str, extra_tags: list[str] | None = None) -> set[str]:
    n = _normalize(text)
    found: set[str] = set(extra_tags or [])
    for tag, kws in TAG_KEYWORDS.items():
        if any(kw.lower() in n for kw in kws):
            found.add(tag)
    if not found:
        found.add("neutral")
    return found


def route_instincts(
    *,
    user_text: str,
    codebook: dict[str, Any],
    max_pick: int = 3,
    extra_tags: list[str] | None = None,
    force_safety: bool = False,
) -> dict[str, Any]:
    tags = _infer_tags(user_text, extra_tags)
    if force_safety or "crisis" in tags:
        tags.add("safety")
        tags.add("crisis")

    scored: list[tuple[int, dict[str, Any]]] = []
    for inst in codebook.get("instincts") or []:
        inst_tags = set(inst.get("tags") or [])
        overlap = len(tags & inst_tags)
        if overlap == 0:
            if tags == {"neutral"} and "neutral" in inst_tags:
                overlap = 1
            else:
                continue
        priority = int(inst.get("priority", 50))
        score = overlap * 10 + priority
        if "safety" in inst_tags or "crisis" in inst_tags:
            if "crisis" in tags or force_safety:
                score += 100
        scored.append((score, inst))

    scored.sort(key=lambda x: (-x[0], x[1]["instinct_id"]))
    picked = [inst for _, inst in scored[:max_pick]]

    if not picked:
        fallback = next(
            (i for i in codebook.get("instincts") or [] if i["instinct_id"] == "inst_tone_neutral"),
            codebook["instincts"][0],
        )
        picked = [fallback]

    composed = "\n".join(f"- [{i['instinct_id']}] {i['instruction_ko']}" for i in picked)
    return {
        "schema": "prompt_codebook_route_v1",
        "version": "1.0.0",
        "hypothesis_class": "HYPO",
        "track": "B",
        "research_only": True,
        "generated_at_utc": _utc_now(),
        "inferred_tags": sorted(tags),
        "selected_instinct_ids": [i["instinct_id"] for i in picked],
        "composed_prompt_fragment_ko": composed,
        "instinct_count": len(picked),
        "codebook_ref": "docs/final/artifacts/prompt_codebook_instincts_v0.json",
        "provenance": {"source": "route_prompt_codebook_instincts_v1"},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--text", required=True)
    ap.add_argument("--codebook-json", type=Path, default=DEFAULT_CODEBOOK)
    ap.add_argument("--max-pick", type=int, default=3)
    ap.add_argument("--tag", action="append", default=[], dest="tags")
    ap.add_argument("--force-safety", action="store_true")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    codebook = _load_json(args.codebook_json)
    report = route_instincts(
        user_text=args.text,
        codebook=codebook,
        max_pick=args.max_pick,
        extra_tags=args.tags or None,
        force_safety=args.force_safety,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "selected": report["selected_instinct_ids"], "out": str(args.out)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
