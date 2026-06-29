#!/usr/bin/env python3
"""Shared loader for A-code governor evening observation append line ([HYPO])."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OBS = ROOT / "reports/a_code_governor_knob_evening_observation_v1_latest.json"
DEFAULT_GATE = ROOT / "reports/a_code_governor_promotion_gate_v1_latest.json"
DEFAULT_READINESS = ROOT / "reports/a_code_promotion_checklist_readiness_v1_latest.json"


def load_governor_evening_observation(path: Path | None = None) -> dict[str, Any] | None:
    obs_path = path or DEFAULT_OBS
    if not obs_path.is_file():
        return None
    doc = json.loads(obs_path.read_text(encoding="utf-8"))
    if doc.get("schema") != "a_code_governor_knob_evening_observation_v1":
        return None
    if not doc.get("evening_append_line"):
        return None
    return doc


def governor_telegram_append_line(path: Path | None = None) -> str | None:
    doc = load_governor_evening_observation(path)
    if not doc:
        return None
    return str(doc["evening_append_line"])


def load_governor_promotion_gate(path: Path | None = None) -> dict[str, Any] | None:
    gate_path = path or DEFAULT_GATE
    if not gate_path.is_file():
        return None
    doc = json.loads(gate_path.read_text(encoding="utf-8"))
    if doc.get("schema") != "a_code_governor_promotion_gate_v1":
        return None
    return doc


def koreanize_evening_ops_line(line: str) -> str:
    """Display-only Korean labels for evening Telegram append lines."""
    repl = (
        ("[HYPO·non-gating]", "[가설·비게이팅]"),
        ("[HYPO]", "[가설]"),
        ("non-gating", "비게이팅"),
        ("human sign-off required", "수동 승인 필요"),
        ("WATCH only", "관측만"),
        ("WATCH_CONTINUE", "관측 지속"),
        ("HOLD_RESEARCH", "연구 유지"),
        ("holdout_consistency=", "홀드아웃 일치="),
        ("profile=local", "프로필=로컬"),
        ("hint=none", "힌트=없음"),
        ("parallel=", "병렬="),
        ("path_cap=", "경로상한="),
        ("Track A/live", "압축A/실매매"),
        ("mechanical+human sign-off OK", "기계+수동 승인 통과"),
        ("research_only", "연구 전용"),
        ("HITL sign-off", "수동 승인"),
    )
    out = line
    for old, new in repl:
        out = out.replace(old, new)
    return out


def governor_gate_summary_line(path: Path | None = None) -> str | None:
    doc = load_governor_promotion_gate(path)
    if not doc:
        return None
    summary = doc.get("summary") or {}
    decision = summary.get("decision")
    if not decision:
        return None
    passed = summary.get("pass_count")
    total = summary.get("total")
    evidence = doc.get("evidence") or {}
    holdout = evidence.get("orchestration_consistency_holdout")
    decision_ko = {
        "WATCH_CONTINUE": "관측 지속",
        "HOLD_RESEARCH": "연구 유지",
    }.get(str(decision or ""), str(decision or "—"))
    return (
        f"▸ A-code 게이트 [가설·비게이팅]: {decision_ko} {passed}/{total} "
        f"홀드아웃 일치={holdout} · 수동 승인 필요 · 관측만"
    )


def promotion_discussion_append_line(path: Path | None = None) -> str | None:
    readiness_path = path or DEFAULT_READINESS
    if not readiness_path.is_file():
        return None
    doc = json.loads(readiness_path.read_text(encoding="utf-8"))
    if doc.get("schema") != "a_code_promotion_checklist_readiness_v1":
        return None
    summary = doc.get("summary") or {}
    if summary.get("promotion_discussion_eligible") is not True:
        return None
    return (
        "▸ A-code RQ-029 [가설·비게이팅]: 기계+수동 승인 통과 — "
        "별 RQ 승격 토의만 가능 · 압축A/실매매 자동 합선 없음"
    )


def append_a_code_evening_lines(
    lines: list[str],
    *,
    include_gate: bool = True,
    include_promotion_hint: bool = True,
) -> None:
    obs_line = governor_telegram_append_line()
    if obs_line:
        lines.extend(["", koreanize_evening_ops_line(obs_line)])
    if include_gate:
        gate_line = governor_gate_summary_line()
        if gate_line:
            lines.append(gate_line)
    if include_promotion_hint:
        hint_line = promotion_discussion_append_line()
        if hint_line:
            lines.append(hint_line)
