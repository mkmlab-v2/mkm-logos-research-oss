#!/usr/bin/env python3
"""TKM encounter_sequence L0 red-flag router attach helpers [HYPO]."""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

L0_TEMPLATE = ROOT / "docs/final/templates/l0_red_flag_escalation_ko_v1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_router():
    path = ROOT / "scripts/l0_red_flag_router_v1.py"
    spec = importlib.util.spec_from_file_location("l0_red_flag_router_v1", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def latest_records_by_sequence_id(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_seq: dict[str, dict[str, Any]] = {}
    for row in records:
        enc = row.get("encounter") if isinstance(row.get("encounter"), dict) else {}
        seq_id = str(enc.get("sequence_id") or "")
        if seq_id:
            by_seq[seq_id] = row
    return list(by_seq.values())


def capture_text_blob(capture: dict[str, Any]) -> str:
    parts: list[str] = []
    ai = capture.get("ai_hypothesis") if isinstance(capture.get("ai_hypothesis"), dict) else {}
    parts.append(str(ai.get("rationale_short") or ""))
    phys = capture.get("physician_constitution") if isinstance(capture.get("physician_constitution"), dict) else {}
    parts.append(str(phys.get("notes") or ""))
    parts.append(str(capture.get("subjective_digest") or ""))
    meta = capture.get("meta") if isinstance(capture.get("meta"), dict) else {}
    parts.append(str(meta.get("subjective_notes") or ""))
    return " ".join(p for p in parts if p.strip())


def sequence_text_blob(record: dict[str, Any]) -> str:
    parts: list[str] = []
    closure = record.get("physician_closure") if isinstance(record.get("physician_closure"), dict) else {}
    phys = closure.get("physician_constitution") if isinstance(closure.get("physician_constitution"), dict) else {}
    parts.append(str(phys.get("notes") or ""))
    for turn in record.get("turns") or []:
        if not isinstance(turn, dict):
            continue
        parts.append(str(turn.get("subjective_digest") or ""))
        ai = turn.get("ai_hypothesis") if isinstance(turn.get("ai_hypothesis"), dict) else {}
        parts.append(str(ai.get("rationale_short") or ""))
    return " ".join(p for p in parts if p.strip())


def evaluate_l0(text_blob: str) -> tuple[bool, list[str]]:
    router = _load_router()
    tpl = router.load_template()
    hits = router.keyword_hits_from_text(text_blob, tpl)
    return bool(hits), hits


def build_l0_event(*, triggered: bool, keyword_hits: list[str], turn_index: int = 0) -> dict[str, Any]:
    return {
        "ts_utc": _utc(),
        "router_stage": "pre_turn",
        "turn_index": turn_index,
        "triggered": triggered,
        "keyword_hits": keyword_hits,
        "escalation_copy_id": "l0_red_flag_escalation_ko_v1",
        "non_gating": True,
    }


def attach_l0_router(
    record: dict[str, Any],
    *,
    capture: dict[str, Any] | None = None,
    force: bool = False,
) -> dict[str, Any]:
    out = dict(record)
    if out.get("l0_router_events") is not None and not force:
        return out

    text = capture_text_blob(capture) if capture else sequence_text_blob(record)
    triggered, hits = evaluate_l0(text)

    turns = list(out.get("turns") or [])
    if turns and isinstance(turns[0], dict):
        turn0 = dict(turns[0])
        if text and not str(turn0.get("subjective_digest") or "").strip():
            turn0["subjective_digest"] = text[:2000]
        if triggered:
            turn0["l0_red_flag"] = build_l0_event(triggered=True, keyword_hits=hits, turn_index=0)
        turns[0] = turn0
        out["turns"] = turns

    out["l0_router_events"] = [build_l0_event(triggered=triggered, keyword_hits=hits, turn_index=0)]
    return out


def is_l0_wired(record: dict[str, Any]) -> bool:
    return isinstance(record.get("l0_router_events"), list)


def validate_l0_sasang_separation(record: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    for ev in record.get("l0_router_events") or []:
        if not isinstance(ev, dict):
            continue
        if ev.get("non_gating") is not True:
            errs.append("l0_router_events.non_gating must be true")
        if "constitution" in ev or "final_ai_constitution" in ev:
            errs.append("l0_router_events must not contain constitution fields")
    for turn in record.get("turns") or []:
        if not isinstance(turn, dict):
            continue
        l0 = turn.get("l0_red_flag")
        if not isinstance(l0, dict):
            continue
        if l0.get("non_gating") is not True:
            errs.append("turn.l0_red_flag.non_gating must be true")
        if "constitution" in l0:
            errs.append("turn.l0_red_flag must not contain constitution")
    summary = record.get("sequence_summary") if isinstance(record.get("sequence_summary"), dict) else {}
    if summary.get("final_ai_constitution") in ("l0_escalation", "red_flag"):
        errs.append("sequence_summary must not be overridden by L0")
    return errs
