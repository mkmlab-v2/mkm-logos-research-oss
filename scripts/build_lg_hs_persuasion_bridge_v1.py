#!/usr/bin/env python3
"""Build LG HS persuasion response from emotion-reasoning state."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE = ROOT / "docs" / "final" / "artifacts" / "mkm_emotion_reasoning_state_v1_latest.json"
DEFAULT_OUT_JSON = ROOT / "docs" / "final" / "artifacts" / "lg_hs_persuasion_bridge_latest.json"
DEFAULT_OUT_MD = ROOT / "docs" / "final" / "artifacts" / "lg_hs_persuasion_bridge_latest.md"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _pick_opening(tone_mode: str) -> str:
    if tone_mode == "de_escalation":
        return (
            "결론부터 말씀드리겠습니다. 저희는 성능 과시보다 안전한 운영을 우선하며, "
            "현재 수치는 로컬 기준선이고 최종값은 타깃 보드 실측 전환으로 확정합니다."
        )
    if tone_mode == "calm":
        return (
            "핵심만 짧게 말씀드리면, 저희의 강점은 고성능 자랑이 아니라 "
            "WATCH/HOLD 기반의 안전 운영 체계와 재현 가능한 검증 루프입니다."
        )
    return (
        "핵심은 두 가지입니다. 현재는 로컬 기준선으로 운영 안정성을 확인했고, "
        "최종 성능은 타깃 보드 실측 전환으로 확정한다는 점입니다."
    )


def _pick_answer(question_type: str, tone_mode: str) -> str:
    concise_prefix = "좋은 질문입니다. "
    if question_type == "performance":
        body = (
            "현재 성능은 로컬 기준선으로 확인했고, Stage3 PASS 및 게이트 상태를 유지하고 있습니다. "
            "다만 양산 확정 수치는 타깃 보드 실측 전환 후 동일 프로토콜로 갱신합니다."
        )
    elif question_type == "safety":
        body = (
            "위험 명령은 WATCH/HOLD 게이트에서 실행 전 차단하고 재질문/거절로 전환합니다. "
            "즉, 정확도 경쟁보다 오작동 전이 억제를 운영 우선순위로 둡니다."
        )
    elif question_type == "schedule":
        body = (
            "주간 검증과 월간 Go/No-Go 게이트로 단계 진입을 통제합니다. "
            "미충족 항목은 즉시 보완 후 재검증하는 보수적 운영 정책을 적용합니다."
        )
    else:
        body = (
            "결론부터 말씀드리면, 저희는 아티팩트 기반 근거로만 답변하고 과장 표현을 배제합니다. "
            "현재는 로컬 기준선, 이후는 타깃 보드 실측 전환으로 확정합니다."
        )

    if tone_mode == "de_escalation":
        return concise_prefix + body
    if tone_mode == "calm":
        return body
    return concise_prefix + body


def _build_doc(state_doc: dict, question_type: str) -> dict:
    schema = state_doc.get("schema")
    if schema != "mkm_emotion_reasoning_state_v1":
        raise ValueError(f"Unexpected state schema: {schema}")

    state = state_doc.get("state", {})
    policy = state_doc.get("policy", {})
    safety = state_doc.get("safety_gate", {})

    tone_mode = str(policy.get("tone_mode", "balanced"))
    opening = _pick_opening(tone_mode)
    answer = _pick_answer(question_type, tone_mode)
    closing = (
        "최종적으로 저희는 성능 과장 대신 실측 기반 확정 원칙을 지키며, "
        "LG 양산 환경에서 안전한 운영 체계로 단계 진입하겠습니다."
    )

    return {
        "schema": "lg_hs_persuasion_bridge_v1",
        "generated_at_utc": _iso_now(),
        "input_state_path": str(DEFAULT_STATE),
        "question_type": question_type,
        "tone_mode": tone_mode,
        "state_summary": {
            "conflict_heat": state.get("conflict_heat"),
            "cooldown_need": state.get("cooldown_need"),
            "risk_sensitivity": state.get("risk_sensitivity"),
            "safety_anchor": state.get("safety_anchor"),
        },
        "response_structure": {
            "opening": opening,
            "answer": answer,
            "closing": closing,
        },
        "guardrails": {
            "fact_lock_required": bool(policy.get("fact_lock_required", True)),
            "blocked_phrases_detected": safety.get("blocked_phrases_detected", []),
            "violation_count": int(safety.get("violation_count", 0)),
            "prohibited_claims": [
                "절대/완벽/100% 보장/제로 리스크",
                "경쟁사 서열 단정",
                "뇌과학 기반 성능 보장 단정",
            ],
        },
        "note": "communication adaptation only; no anthropomorphic claims",
    }


def _to_markdown(doc: dict) -> str:
    rs = doc["response_structure"]
    ss = doc["state_summary"]
    gd = doc["guardrails"]
    return (
        "# LG HS Persuasion Bridge Latest\n\n"
        f"- generated_at_utc: `{doc['generated_at_utc']}`\n"
        f"- question_type: `{doc['question_type']}`\n"
        f"- tone_mode: `{doc['tone_mode']}`\n\n"
        "## State Summary\n\n"
        f"- conflict_heat: `{ss['conflict_heat']}`\n"
        f"- cooldown_need: `{ss['cooldown_need']}`\n"
        f"- risk_sensitivity: `{ss['risk_sensitivity']}`\n"
        f"- safety_anchor: `{ss['safety_anchor']}`\n\n"
        "## Response (Conclusion -> Evidence -> Boundary)\n\n"
        f"- opening: {rs['opening']}\n"
        f"- answer: {rs['answer']}\n"
        f"- closing: {rs['closing']}\n\n"
        "## Guardrails\n\n"
        f"- fact_lock_required: `{gd['fact_lock_required']}`\n"
        f"- violation_count: `{gd['violation_count']}`\n"
        f"- blocked_phrases_detected: `{gd['blocked_phrases_detected']}`\n"
    )


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--state-json", type=Path, default=DEFAULT_STATE)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT_JSON)
    ap.add_argument("--output-md", type=Path, default=DEFAULT_OUT_MD)
    ap.add_argument(
        "--question-type",
        default="general",
        choices=["general", "performance", "safety", "schedule"],
    )
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    state_doc = _load_json(args.state_json)
    doc = _build_doc(state_doc, args.question_type)

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.output_md.write_text(_to_markdown(doc), encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "output_json": str(args.output_json),
                "output_md": str(args.output_md),
                "tone_mode": doc["tone_mode"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
