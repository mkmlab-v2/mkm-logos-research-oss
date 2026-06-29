#!/usr/bin/env python3
"""AI vs physician constitution match rate — clinic capture + encounter_sequence [HYPO]."""

from __future__ import annotations

from typing import Any

SASANG_LABELS = frozenset({"taeeum", "soyang", "taeyang", "soeum"})


def _last_turn_ai_label(row: dict[str, Any]) -> str:
    turns = row.get("turns")
    if not isinstance(turns, list):
        return ""
    for turn in reversed(turns):
        if not isinstance(turn, dict):
            continue
        hyp = turn.get("ai_hypothesis") if isinstance(turn.get("ai_hypothesis"), dict) else {}
        cand = str(hyp.get("constitution") or "")
        if cand in SASANG_LABELS:
            return cand
    return ""


def extract_ai_physician_labels(row: dict[str, Any]) -> tuple[str, str] | None:
    """Return comparable (ai_label, physician_label) or None if not comparable."""
    ai = row.get("ai_hypothesis") if isinstance(row.get("ai_hypothesis"), dict) else {}
    pc = row.get("physician_constitution") if isinstance(row.get("physician_constitution"), dict) else {}

    closure = row.get("physician_closure") if isinstance(row.get("physician_closure"), dict) else {}
    if closure:
        closure_pc = closure.get("physician_constitution")
        if isinstance(closure_pc, dict):
            pc = closure_pc

    ai_l = str(ai.get("constitution") or "")
    if ai_l not in SASANG_LABELS:
        summary = row.get("sequence_summary") if isinstance(row.get("sequence_summary"), dict) else {}
        ai_l = str(summary.get("final_ai_constitution") or "")
    if ai_l not in SASANG_LABELS:
        ai_l = _last_turn_ai_label(row)

    phy_l = str(pc.get("label") or "")
    if ai_l in SASANG_LABELS and phy_l in SASANG_LABELS:
        return ai_l, phy_l
    return None


def _record_match(row: dict[str, Any]) -> bool | None:
    agr = row.get("agreement")
    if isinstance(agr, dict) and "ai_physician_match" in agr:
        return bool(agr["ai_physician_match"])
    closure = row.get("physician_closure")
    if isinstance(closure, dict):
        closure_agr = closure.get("agreement")
        if isinstance(closure_agr, dict) and "ai_physician_match" in closure_agr:
            return bool(closure_agr["ai_physician_match"])
    pair = extract_ai_physician_labels(row)
    if pair is None:
        return None
    return pair[0] == pair[1]


def match_rate(rows: list[dict[str, Any]]) -> float | None:
    comparable = 0
    matches = 0
    for row in rows:
        m = _record_match(row)
        if m is None:
            continue
        comparable += 1
        if m:
            matches += 1
    if not comparable:
        return None
    return round(matches / comparable, 4)
