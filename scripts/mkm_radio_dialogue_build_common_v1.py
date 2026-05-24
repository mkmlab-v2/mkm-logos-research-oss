"""O-P31c shared builders for radio_dialogue_script_v1 (Zone B)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from scripts.mkm_radio_dialogue_guard_v1 import (
    CLOSING_CTA_KO,
    DISCLAIMER_TEXT_KO,
    sanitize_public_audio_text,
)

# edge-tts ko-KR catalog (2026-05): SunHi, InJoon, HyunsuMultilingual only
VOICES = {
    "system_announcer": "ko-KR-SunHiNeural",
    "dj_logos": "ko-KR-InJoonNeural",
    "mc_myeongni": "ko-KR-HyunsuMultilingualNeural",
    "dr_sasang": "ko-KR-SunHiNeural",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_json(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def clip(s: str, n: int) -> str:
    s = (s or "").strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def resolve_path(root: Path, p: Path) -> Path:
    return p if p.is_absolute() else root / p


def myeongni_pacing_line(briefing: Dict[str, Any], fortune: Dict[str, Any]) -> str:
    lines = fortune.get("myeongni_lines") or []
    one = clip(str(lines[0] if lines else ""), 120)
    if one.startswith("▸"):
        one = one.lstrip("▸ ").strip()
    stream = briefing.get("hypothesis_stream") or {}
    branches = stream.get("branches") or []
    branch = branches[0] if branches and isinstance(branches[0], dict) else {}
    bias = clip(str(branch.get("predicted_bias_ko") or ""), 80)
    wp = briefing.get("world_pulse") or {}
    action = str((wp.get("kospi") or {}).get("today_action") or "WATCH")
    posture = "관측·페이싱" if action == "WATCH" else "리듬 조절"
    base = f"MC 명리입니다. 오늘 리듬은 {posture} 쪽입니다. {clip(one, 70)} "
    if bias:
        base += f"행동 힌트: {bias} "
    base += "중요한 결정은 한 박자 늦추고 검증하십시오."
    return sanitize_public_audio_text(base)


def logos_line(logos: Dict[str, Any]) -> str:
    anchor = logos.get("golden_anchor") or {}
    ref = anchor.get("ref") or "—"
    text = clip(str(anchor.get("text") or ""), 90)
    theme = clip(str(anchor.get("theme") or logos.get("theme_stem") or ""), 40)
    return sanitize_public_audio_text(
        f"DJ Logos입니다. 오늘의 거울은 {theme}, {ref}. {text} "
        "역사적 맥락은 관측용이며, 투자·의료 단정이 아닙니다."
    )


def logos_story_line(logos: Dict[str, Any], story_body: str) -> str:
    anchor = logos.get("golden_anchor") or {}
    ref = anchor.get("ref") or "—"
    return sanitize_public_audio_text(
        f"DJ Logos입니다. 사연을 역사적 거울에 비춰 보겠습니다. {clip(story_body, 160)} "
        f"오늘 연결 구절 {ref}. 투자·치료 조언이 아닌 관측입니다."
    )


def sasang_brake_line(briefing: Dict[str, Any], *, extra: str = "") -> str:
    uc = briefing.get("user_condition") or {}
    stress = str(uc.get("stress_band") or "mid")
    stream = briefing.get("hypothesis_stream") or {}
    synth = clip(str(stream.get("synthesis_ko") or ""), 100)
    stress_note = "높음" if stress == "high" else stress
    tail = f" {clip(extra, 80)}" if extra else ""
    return sanitize_public_audio_text(
        f"닥터 사상입니다. 스트레스 밴드 {stress_note}, 조급·과반응 편향이 보입니다. "
        f"{synth}{tail} "
        "오늘은 확장보다 브레이크: 수면·수분·한 박자 휴식을 우선하십시오."
    )


def macro_posture_line(briefing: Dict[str, Any]) -> str:
    wp = briefing.get("world_pulse") or {}
    macro = wp.get("macro") or {}
    risk = str(macro.get("risk_warning_level") or "elevated")
    posture = str(macro.get("operator_posture") or "watch")
    return sanitize_public_audio_text(
        f"세계 판면은 비가격 관측 모드입니다. 리스크 밴드 {risk}, 자세 {posture}. "
        "시세·적중률 수치는 방송에 넣지 않습니다."
    )


def story_narration_line(story: Dict[str, Any]) -> str:
    title = clip(str(story.get("title_ko") or "익명 사연"), 40)
    body = clip(str(story.get("body_ko") or ""), 220)
    return sanitize_public_audio_text(
        f"야간 부스입니다. 오늘 사연 제목, {title}. {body} "
        "실명·시세·주문 조언은 다루지 않습니다."
    )


class DialogueLineFactory:
    def __init__(self) -> None:
        self._seq = 0

    def line(
        self,
        persona: str,
        text: str,
        *,
        tags: Optional[List[str]] = None,
        evidence: str = "",
        dur: float = 12.0,
    ) -> Dict[str, Any]:
        self._seq += 1
        return {
            "sequence": self._seq,
            "persona": persona,
            "voice_profile_id": VOICES[persona],
            "audio_text": sanitize_public_audio_text(text),
            "copy_tags": tags or [],
            "evidence_ref": evidence,
            "target_duration_sec": dur,
        }


def base_doc_shell(
    *,
    briefing_id: str,
    calendar_kst: str,
    program_style: str,
    deployment_target: str,
    upstream_inputs: Dict[str, Any],
    srt_name: str,
    program_skin: str = "mkm_radio",
) -> Dict[str, Any]:
    return {
        "schema": "radio_dialogue_script_v1",
        "version": "1.0.0",
        "briefing_id": briefing_id,
        "generated_at_utc": utc_now(),
        "calendar_kst": calendar_kst,
        "hypothesis_tier": "B",
        "non_gating": True,
        "boundary_ack": True,
        "program_skin": program_skin,
        "program_style": program_style,
        "deployment_target": deployment_target,
        "gates": {
            "public_facing_version": "1.7",
            "spoken_price_allowed": False,
            "human_review_required": True,
            "track_a_webhook_count": 0,
        },
        "track_wall": {
            "live_trading_trigger": False,
            "track_a_order_path": False,
            "clinical_diagnosis": False,
        },
        "market_context_pointer": {
            "macro_band_snapshot": "reports/op31b_shadow/market_snapshot_latest.json",
            "spoken_price_allowed": False,
        },
        "upstream_inputs": upstream_inputs,
        "caption_config": {
            "burn_in_subtitle": True,
            "srt_output_path": srt_name,
        },
    }
