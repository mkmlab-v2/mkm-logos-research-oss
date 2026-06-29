#!/usr/bin/env python3
"""PersonaDiary voice → 4-lane segment classifier v1 [HYPO].

B-track only. Rule-based (no LLM). SOAP/clinical outputs forbidden.
Reuses consumer copy forbidden scan from personadiary_consumer_copy_v1.
"""
from __future__ import annotations

import json
import re
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

LANES = ("body", "mind", "work", "rest")
SOURCE = "voice_hypo_v1"
SCHEMA_OUT = "personadiary_voice_lane_classification_hypo_v1"

_LANE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "body": (
        "수면",
        "잠",
        "몸",
        "통증",
        "아프",
        "식사",
        "밥",
        "운동",
        "컨디션",
        "피곤",
        "두통",
        "소화",
        "몸무게",
        "건강",
    ),
    "mind": (
        "기분",
        "마음",
        "불안",
        "우울",
        "스트레스",
        "걱정",
        "짜증",
        "외로",
        "스크롤",
        "숏폼",
        "집중",
        "산만",
        "자책",
        "비교",
        "관계",
        "감정",
    ),
    "work": (
        "업무",
        "일",
        "마감",
        "회의",
        "프로젝트",
        "할일",
        "출근",
        "보고",
        "미팅",
        "과제",
        "직장",
        "업체",
    ),
    "rest": (
        "휴식",
        "쉼",
        "쉬",
        "여가",
        "명상",
        "산책",
        "독서",
        "음악",
        "취미",
        "휴가",
        "낮잠",
    ),
}

_PRIORITY = ("work", "body", "mind", "rest")

_CLINICAL_FORBIDDEN = (
    "soap",
    "주관적",
    "객관적",
    "평가",
    "계획",
    "체질",
    "소음인",
    "소양인",
    "태음인",
    "태양인",
    "탕",
    "처방",
    "진단",
)

_WATCH_KEYWORDS = (
    "새벽",
    "두 시",
    "2시",
    "02:",
    "숏폼",
    "스크롤",
    "네 시간",
    "4시간",
    "못 잤",
    "잠 못",
    "밤새",
)

_SHIELD_KEYWORDS = (
    "자해",
    "죽고 싶",
    "살고 싶지",
    "극단적",
    "약물 남용",
    "약을 많이",
)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def _split_segments(text: str) -> list[str]:
    raw = (text or "").replace("\r\n", "\n").strip()
    if not raw:
        return []
    parts = re.split(r"(?<=[.!?…])\s+|\n+", raw)
    return [p.strip() for p in parts if p.strip()]


def _lane_scores(segment: str) -> dict[str, int]:
    norm = _normalize(segment).lower()
    scores = {lane: 0 for lane in LANES}
    matched: dict[str, list[str]] = {lane: [] for lane in LANES}
    for lane, keywords in _LANE_KEYWORDS.items():
        for kw in keywords:
            if kw in norm:
                scores[lane] += 1
                matched[lane].append(kw)
    return scores, matched


def _pick_lane(
    scores: dict[str, int],
    *,
    active_lane_hint: str | None = None,
) -> tuple[str, float, list[str]]:
    best = max(scores.values())
    if best == 0:
        hint = active_lane_hint if active_lane_hint in LANES else "mind"
        return hint, 0.45, []

    winners = [lane for lane in _PRIORITY if scores[lane] == best]
    if active_lane_hint in winners:
        lane = active_lane_hint
    else:
        lane = winners[0]
    confidence = min(0.95, 0.5 + 0.1 * best)
    return lane, round(confidence, 2), []


def _clinical_forbidden_hits(text: str) -> list[str]:
    norm = _normalize(text).lower()
    hits: list[str] = []
    for token in _CLINICAL_FORBIDDEN:
        if token.lower() in norm:
            hits.append(f"clinical_forbidden:{token}")
    return hits


def _mind_red_flag_tier(full_text: str, segments: list[dict[str, Any]]) -> str:
    norm = _normalize(full_text).lower()
    if any(kw in norm for kw in _SHIELD_KEYWORDS):
        return "shield_hypo"
    if any(kw in norm for kw in _WATCH_KEYWORDS):
        return "watch"
    if any(s.get("blocked") for s in segments):
        return "blocked"
    return "none"


def classify_voice_transcript(
    text: str,
    *,
    active_lane_hint: str | None = None,
    stt_event_id: str | None = None,
) -> dict[str, Any]:
    """Classify transcript into lane segments with mind red-flag tier."""
    from personadiary_consumer_copy_v1 import find_forbidden_violations

    chunks = _split_segments(text)
    if not chunks and text.strip():
        chunks = [_normalize(text)]

    segments: list[dict[str, Any]] = []
    for chunk in chunks:
        violations = find_forbidden_violations(chunk)
        clinical = _clinical_forbidden_hits(chunk)
        blocked = bool(violations or clinical)

        if blocked:
            segments.append(
                {
                    "lane": "mind",
                    "text": chunk,
                    "confidence": 0.0,
                    "source": SOURCE,
                    "needs_review": True,
                    "blocked": True,
                    "violation_codes": violations + clinical,
                }
            )
            continue

        scores, matched = _lane_scores(chunk)
        lane, confidence, _ = _pick_lane(scores, active_lane_hint=active_lane_hint)
        needs_review = confidence < 0.55
        if needs_review:
            lane = "mind"

        segments.append(
            {
                "lane": lane,
                "text": chunk,
                "confidence": confidence,
                "source": SOURCE,
                "needs_review": needs_review,
                "blocked": False,
                "matched_keywords": matched.get(lane, [])[:5],
            }
        )

    full_text = "\n".join(chunks)
    tier = _mind_red_flag_tier(full_text, segments)
    human_gate = tier in ("shield_hypo", "blocked") or any(
        s.get("needs_review") or s.get("blocked") for s in segments
    )

    return {
        "schema": SCHEMA_OUT,
        "version": 1,
        "hypothesis_tier": "B",
        "preview_only": True,
        "send_gate_default": "HOLD",
        "stt_event_id": stt_event_id,
        "active_lane_hint": active_lane_hint,
        "segments": segments,
        "mind_red_flag_tier": tier,
        "human_gate_required": human_gate,
        "forbidden_blocked_count": sum(1 for s in segments if s.get("blocked")),
    }


def load_transcript_json(path: Path) -> dict[str, Any]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    if doc.get("schema") != "personadiary_voice_transcript_hypo_v1":
        raise ValueError(f"unexpected_transcript_schema: {doc.get('schema')}")
    utterances = doc.get("utterances") or []
    if not isinstance(utterances, list):
        raise ValueError("utterances_must_be_list")
    text = "\n".join(str(u).strip() for u in utterances if str(u).strip())
    return {
        "text": text,
        "active_lane_hint": doc.get("active_lane_hint"),
        "stt_event_id": doc.get("stt_event_id"),
    }


def main() -> int:
    import argparse
    import sys

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--text", default="", help="Raw transcript UTF-8")
    ap.add_argument("--transcript-json", type=Path, help="Fixture or STT export JSON")
    ap.add_argument("--active-lane-hint", choices=LANES, default=None)
    ap.add_argument("--stt-event-id", default=None)
    ap.add_argument("--session-id", default="personadiary-cli")
    ap.add_argument("--append-stt-audit", action="store_true")
    ap.add_argument(
        "--stt-audit-out",
        type=Path,
        default=ROOT / "reports" / "stt_routing_audit_log_v1.jsonl",
    )
    ap.add_argument("--out-json", type=Path, default=None)
    args = ap.parse_args()

    text = args.text
    hint = args.active_lane_hint
    stt_id = args.stt_event_id

    if args.transcript_json:
        loaded = load_transcript_json(args.transcript_json)
        text = loaded["text"]
        hint = hint or loaded.get("active_lane_hint")
        stt_id = stt_id or loaded.get("stt_event_id")

    if not text and not sys.stdin.isatty():
        text = sys.stdin.read()

    if not text.strip():
        print("usage: provide --text, --transcript-json, or stdin", file=sys.stderr)
        return 1

    if not stt_id:
        stt_id = str(uuid.uuid4())

    out = classify_voice_transcript(
        text,
        active_lane_hint=hint,
        stt_event_id=stt_id,
    )

    audit_row = None
    from build_personadiary_stt_audit_row_hypo_v1 import (
        append_stt_audit_row,
        build_paste_stt_audit_row,
        validate_stt_audit_row,
    )

    audit_row = build_paste_stt_audit_row(
        event_id=stt_id,
        transcript=text,
        session_id=args.session_id or None,
    )
    validate_stt_audit_row(audit_row, ROOT / "docs/final/schemas/stt_routing_audit_log_v1.schema.json")
    out["stt_audit_row"] = audit_row
    out["stt_audit_linked"] = out.get("stt_event_id") == audit_row["event_id"]
    if args.append_stt_audit:
        append_stt_audit_row(audit_row, args.stt_audit_out)

    payload = json.dumps(out, ensure_ascii=False, indent=2)
    if args.out_json:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
