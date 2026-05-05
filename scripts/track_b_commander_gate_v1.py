# -*- coding: utf-8 -*-
"""Track B 공통: 지휘관 최종권·기계는 관측 보조 (단일 SSOT dict)."""

from __future__ import annotations

from typing import Any

HUMAN_COMMANDER_GATE_V1: dict[str, Any] = {
    "schema": "human_commander_gate_v1",
    "version": "1.0.0",
    "track": "B",
    "banner_ko": "[TRACK B / HYPO] 연구용·비자동 — 최종 채택은 지휘관 판단 대기",
    "final_authority": "human_commander",
    "machine_output_role": "decision_support_observation_only",
}
