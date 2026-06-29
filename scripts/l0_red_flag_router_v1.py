#!/usr/bin/env python3
"""L0 red-flag router for TKM patient-facing + han physician turn [HYPO]."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = ROOT / "docs/final/templates/l0_red_flag_escalation_ko_v1.json"


def load_template(path: Path | None = None) -> dict[str, Any]:
    p = path or TEMPLATE_PATH
    if not p.is_file():
        raise FileNotFoundError(f"L0 template missing: {p}")
    return json.loads(p.read_text(encoding="utf-8-sig"))


def keyword_hits_from_text(text: str, template: dict[str, Any]) -> list[str]:
    hits: list[str] = []
    groups = template.get("keyword_groups") if isinstance(template.get("keyword_groups"), dict) else {}
    blob = (text or "").lower()
    for _group, keywords in groups.items():
        if not isinstance(keywords, list):
            continue
        for kw in keywords:
            s = str(kw).strip()
            if s and s.lower() in blob:
                hits.append(s)
    return hits


def _dedupe_hits(hits: list[str]) -> list[str]:
    seen: set[str] = set()
    uniq: list[str] = []
    for h in hits:
        if h not in seen:
            seen.add(h)
            uniq.append(h)
    return uniq


def _l0_state_from_hits(hits: list[str], *, escalation_copy_id: str | None = None) -> dict[str, Any]:
    uniq = _dedupe_hits(hits)
    return {
        "triggered": bool(uniq),
        "keyword_hits": uniq,
        "escalation_copy_id": escalation_copy_id or "l0_red_flag_escalation_ko_v1",
        "template_id": "l0_red_flag_escalation_ko_v1",
    }


def merge_l0_states(*states: dict[str, Any] | None) -> dict[str, Any]:
    hits: list[str] = []
    triggered = False
    escalation_copy_id = None
    for state in states:
        if not state:
            continue
        if state.get("triggered") is True:
            triggered = True
        hits.extend([str(x) for x in state.get("keyword_hits") or []])
        escalation_copy_id = state.get("escalation_copy_id") or escalation_copy_id
    return _l0_state_from_hits(hits, escalation_copy_id=escalation_copy_id) if triggered else {
        "triggered": False,
        "keyword_hits": [],
        "escalation_copy_id": escalation_copy_id or "l0_red_flag_escalation_ko_v1",
        "template_id": "l0_red_flag_escalation_ko_v1",
    }


def collect_l0_state_from_sequence(sequence: dict[str, Any]) -> dict[str, Any]:
    hits: list[str] = []
    triggered = False
    escalation_copy_id = None
    tmpl = load_template()
    for ev in sequence.get("l0_router_events") or []:
        if not isinstance(ev, dict):
            continue
        if ev.get("triggered") is True:
            triggered = True
            hits.extend([str(x) for x in ev.get("keyword_hits") or []])
            escalation_copy_id = ev.get("escalation_copy_id") or escalation_copy_id
    for turn in sequence.get("turns") or []:
        if not isinstance(turn, dict):
            continue
        l0 = turn.get("l0_red_flag")
        if isinstance(l0, dict) and l0.get("triggered") is True:
            triggered = True
            hits.extend([str(x) for x in l0.get("keyword_hits") or []])
            escalation_copy_id = l0.get("escalation_copy_id") or escalation_copy_id
        digest = str(turn.get("subjective_digest") or "")
        hits.extend(keyword_hits_from_text(digest, tmpl))
        if hits:
            triggered = True
    if not triggered:
        return merge_l0_states()
    return _l0_state_from_hits(hits, escalation_copy_id=escalation_copy_id)


def _soap_text(soap: dict[str, Any], key: str) -> str:
    block = soap.get(key)
    if isinstance(block, dict):
        return str(block.get("text") or "").strip()
    return str(block or "").strip()


def collect_l0_scan_text_from_bundle(
    bundle: dict[str, Any],
    intake: dict[str, Any] | None = None,
) -> str:
    parts: list[str] = []
    soap = bundle.get("clinical_soap_v1") if isinstance(bundle.get("clinical_soap_v1"), dict) else {}
    for key in ("subjective", "objective", "assessment", "plan"):
        text = _soap_text(soap, key)
        if text:
            parts.append(text)
    intake_root = intake if isinstance(intake, dict) else {}
    intake_block = intake_root.get("intake") if isinstance(intake_root.get("intake"), dict) else intake_root
    for field in ("symptoms", "situation", "subjective_notes", "gynecology_note", "endocrine_note"):
        val = intake_block.get(field)
        if isinstance(val, list):
            parts.extend(str(x) for x in val)
        elif val:
            parts.append(str(val))
    return "\n".join(parts)


def collect_l0_state_from_bundle(
    bundle: dict[str, Any],
    intake: dict[str, Any] | None = None,
) -> dict[str, Any]:
    tmpl = load_template()
    blob = collect_l0_scan_text_from_bundle(bundle, intake)
    hits = keyword_hits_from_text(blob, tmpl)
    return _l0_state_from_hits(hits)


def format_patient_markdown_block(l0_state: dict[str, Any], template: dict[str, Any] | None = None) -> str:
    if not l0_state.get("triggered"):
        return ""
    tpl = template or load_template()
    hits = l0_state.get("keyword_hits") or []
    hit_line = f"- 감지 키워드(참고): `{', '.join(hits)}`\n" if hits else ""
    return (
        "> **L0 안전 알림 (non-gating)** — AI 진단·처방·응급 판정이 **아닙니다**.\n\n"
        f"### {tpl.get('headline_ko', '')}\n\n"
        f"{tpl.get('body_ko', '')}\n\n"
        f"{hit_line}\n"
        f"_{tpl.get('footer_ko', '')}_\n\n"
        "---\n\n"
    )


def format_han_turn_l0_layer(l0_state: dict[str, Any], template: dict[str, Any] | None = None) -> dict[str, Any]:
    tpl = template or load_template()
    if not l0_state.get("triggered"):
        return {
            "red_flags_ko": ["번들·문진 기반 — 추가 red flag 문진 필요"],
            "escalation_ko": "응급 신호 시 대면/응급 경로 우선",
            "soap_assessment_excerpt": "",
            "l0_router_triggered": False,
        }
    hits = l0_state.get("keyword_hits") or []
    return {
        "red_flags_ko": [str(tpl.get("headline_ko") or ""), f"키워드: {', '.join(hits)}" if hits else "키워드 감지"],
        "escalation_ko": str(tpl.get("body_ko") or ""),
        "soap_assessment_excerpt": "(L0 router — SOAP 발췌 전 red-flag 우선)",
        "l0_router_triggered": True,
        "escalation_copy_id": l0_state.get("escalation_copy_id"),
        "template_id": l0_state.get("template_id"),
    }


def load_sequence_for_bundle(bundle: dict[str, Any], *, workspace_root: Path | None = None) -> dict[str, Any] | None:
    root = workspace_root or ROOT
    prov = bundle.get("provenance") if isinstance(bundle.get("provenance"), dict) else {}
    seq_id = str(prov.get("encounter_sequence_id") or "").strip()
    ledger_ref = str(prov.get("encounter_sequence_ledger_ref") or "").strip()
    if not seq_id or not ledger_ref:
        return None
    path = root / ledger_ref
    if not path.is_file():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        enc = row.get("encounter") if isinstance(row.get("encounter"), dict) else {}
        if str(enc.get("sequence_id") or "") == seq_id:
            return row
    return None
