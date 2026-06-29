#!/usr/bin/env python3
"""Classify dummy vs physician_gold rows for TKM clinic/encounter ledgers [HYPO]."""

from __future__ import annotations

from typing import Any


def is_dummy_clinic_capture(row: dict[str, Any]) -> bool:
    meta = row.get("meta") if isinstance(row.get("meta"), dict) else {}
    if meta.get("dummy_autofill") is True:
        return True
    ai = row.get("ai_hypothesis") if isinstance(row.get("ai_hypothesis"), dict) else {}
    if str(ai.get("model_id") or "") == "dummy_autofill_v1":
        return True
    rationale = str(ai.get("rationale_short") or "")
    if "[DUMMY]" in rationale:
        return True
    enc = row.get("encounter") if isinstance(row.get("encounter"), dict) else {}
    ref = str(enc.get("ref_token") or "")
    if ref.startswith("ENC-DUMMY-"):
        return True
    lane = str(row.get("label_lane") or "")
    if lane == "consumer_survey_only":
        return True
    return False


def is_dummy_encounter_sequence(row: dict[str, Any]) -> bool:
    prov = row.get("provenance") if isinstance(row.get("provenance"), dict) else {}
    if str(prov.get("generator_id") or "") == "dummy_autofill_v1":
        return True
    enc = row.get("encounter") if isinstance(row.get("encounter"), dict) else {}
    seq = str(enc.get("sequence_id") or "")
    if seq.startswith("SEQ-DUMMY-"):
        return True
    ref = str(enc.get("ref_token") or "")
    if ref.startswith("ENC-DUMMY-"):
        return True
    for turn in row.get("turns") or []:
        if not isinstance(turn, dict):
            continue
        hyp = turn.get("ai_hypothesis") if isinstance(turn.get("ai_hypothesis"), dict) else {}
        if str(hyp.get("model_id") or "") == "dummy_autofill_v1":
            return True
    return False
