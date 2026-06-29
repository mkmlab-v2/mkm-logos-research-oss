#!/usr/bin/env python3
"""Per-case alignment backend routing for ko shorts STT [HYPO]."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.ko_shorts_alignment_backend_lib_v1 import (
    BACKEND_FASTER_WHISPER,
    BACKEND_STABLE_TS,
    BACKEND_WHISPERX,
    benchmark_alignment_backend_v1,
)

MODE_AUTO = "auto"
MODE_BENCH_ALL = "bench_all"
MODE_FASTER_WHISPER = "faster_whisper"
MODE_STABLE_TS = "stable_ts"
MODE_WHISPERX = "whisperx"

CLI_MODES = frozenset(
    {MODE_AUTO, MODE_BENCH_ALL, MODE_FASTER_WHISPER, MODE_STABLE_TS, MODE_WHISPERX}
)

MODE_TO_BACKEND = {
    MODE_FASTER_WHISPER: BACKEND_FASTER_WHISPER,
    MODE_STABLE_TS: BACKEND_STABLE_TS,
    MODE_WHISPERX: BACKEND_WHISPERX,
}

FALLBACK_BACKEND = BACKEND_FASTER_WHISPER

ROUTING_RULES_V1: list[dict[str, Any]] = [
    {
        "id": "traditional_vocal_hint",
        "match": {"domain_hint": ["traditional_vocal", "pansori", "gugak"]},
        "backend": BACKEND_WHISPERX,
        "reason": "domain_hint traditional vocal / pansori",
    },
    {
        "id": "case_id_pansori",
        "match": {"case_id_contains": ["pansori"]},
        "backend": BACKEND_WHISPERX,
        "reason": "case_id pansori — bench lower P0-P1 gap vs faster-whisper",
    },
]

ROUTING_DEFAULT = {
    "backend": BACKEND_FASTER_WHISPER,
    "reason": "default faster_whisper_word_ts — cost/latency baseline",
}


def normalize_cli_mode_v1(mode: str) -> str:
    m = (mode or MODE_AUTO).strip().lower()
    if m in ("faster-whisper", "faster_whisper_word_ts"):
        return MODE_FASTER_WHISPER
    if m not in CLI_MODES:
        raise ValueError(f"unknown alignment-backend mode: {mode}")
    return m


def _case_id_matches(case_id: str, tokens: list[str]) -> bool:
    cid = case_id.lower()
    return any(t.lower() in cid for t in tokens)


def _hint_matches(domain_hint: str | None, hints: list[str]) -> bool:
    if not domain_hint:
        return False
    dh = domain_hint.lower()
    return any(h.lower() == dh for h in hints)


def resolve_alignment_backend_v1(
    *,
    case_id: str,
    mode: str = MODE_AUTO,
    domain_hint: str | None = None,
    alignment_backend_override: str | None = None,
) -> dict[str, Any]:
    """Resolve backend for one case. Drift KPI only — not lip-sync pass."""
    if alignment_backend_override:
        backend = alignment_backend_override
        return {
            "case_id": case_id,
            "backend": backend,
            "rule_id": "override",
            "reason": "alignment_backend_override",
            "mode": mode,
            "domain_hint": domain_hint,
        }

    normalized = normalize_cli_mode_v1(mode)
    if normalized in MODE_TO_BACKEND:
        return {
            "case_id": case_id,
            "backend": MODE_TO_BACKEND[normalized],
            "rule_id": f"cli_{normalized}",
            "reason": f"explicit --alignment-backend {normalized}",
            "mode": normalized,
            "domain_hint": domain_hint,
        }

    for rule in ROUTING_RULES_V1:
        match = rule.get("match") or {}
        if _hint_matches(domain_hint, list(match.get("domain_hint") or [])):
            return {
                "case_id": case_id,
                "backend": rule["backend"],
                "rule_id": rule["id"],
                "reason": rule.get("reason"),
                "mode": MODE_AUTO,
                "domain_hint": domain_hint,
            }
        if _case_id_matches(case_id, list(match.get("case_id_contains") or [])):
            return {
                "case_id": case_id,
                "backend": rule["backend"],
                "rule_id": rule["id"],
                "reason": rule.get("reason"),
                "mode": MODE_AUTO,
                "domain_hint": domain_hint,
            }

    return {
        "case_id": case_id,
        "backend": ROUTING_DEFAULT["backend"],
        "rule_id": "default",
        "reason": ROUTING_DEFAULT["reason"],
        "mode": MODE_AUTO,
        "domain_hint": domain_hint,
    }


def load_routing_sidecar_v1(path: Path | None) -> dict[str, dict[str, Any]]:
    if not path or not path.is_file():
        return {}
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(doc, dict) and "cases" in doc:
        return {str(k): dict(v) for k, v in (doc.get("cases") or {}).items()}
    if isinstance(doc, dict):
        return {str(k): dict(v) for k, v in doc.items() if isinstance(v, dict)}
    return {}


def build_alignment_routing_table_v1(
    case_ids: list[str],
    *,
    mode: str = MODE_AUTO,
    sidecar: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    sidecar = sidecar or {}
    rows: list[dict[str, Any]] = []
    for case_id in case_ids:
        meta = sidecar.get(case_id) or {}
        rows.append(
            resolve_alignment_backend_v1(
                case_id=case_id,
                mode=mode,
                domain_hint=meta.get("domain_hint"),
                alignment_backend_override=meta.get("alignment_backend_override"),
            )
        )
    return rows


def alignment_routing_contract_v1() -> dict[str, Any]:
    return {
        "schema": "ko_shorts_alignment_routing_v1",
        "research_only": True,
        "send_gate": "HOLD",
        "default_backend": ROUTING_DEFAULT["backend"],
        "fallback_backend": FALLBACK_BACKEND,
        "rules": ROUTING_RULES_V1,
        "cli_modes": sorted(CLI_MODES),
        "domain_hint_priority": "override > cli explicit > domain_hint rule > case_id rule > default",
        "evidence_pointer": "reports/ko_shorts_alignment_backend_spike_v1_latest.json",
    }


def backends_for_bench_all_v1(*, include_stable_ts: bool, include_whisperx: bool) -> tuple[str, ...]:
    backends: list[str] = [BACKEND_FASTER_WHISPER]
    if include_stable_ts:
        backends.append(BACKEND_STABLE_TS)
    if include_whisperx:
        backends.append(BACKEND_WHISPERX)
    return tuple(backends)


def benchmark_routed_backend_v1(
    media_path: Path,
    backend: str,
    *,
    model_name: str = "small",
    allow_fallback: bool = True,
) -> dict[str, Any]:
    result = benchmark_alignment_backend_v1(
        media_path,
        backend,
        model_name=model_name,
        p0_whisper_semantic=(backend == BACKEND_FASTER_WHISPER),
    )
    entry: dict[str, Any] = {
        "backend": backend,
        "ok": result.get("ok"),
        "error": result.get("error"),
        "routing_fallback": False,
        "result": result,
    }
    if allow_fallback and backend != FALLBACK_BACKEND and not result.get("ok"):
        fb = benchmark_alignment_backend_v1(
            media_path,
            FALLBACK_BACKEND,
            model_name=model_name,
            p0_whisper_semantic=True,
        )
        entry["routing_fallback"] = True
        entry["fallback_backend"] = FALLBACK_BACKEND
        entry["fallback_result"] = fb
        entry["ok"] = bool(fb.get("ok"))
        entry["result"] = fb if fb.get("ok") else result
        entry["error"] = None if fb.get("ok") else result.get("error")
    return entry


def parse_domain_hint_from_filename_v1(filename: str) -> str | None:
    """Optional P1 helper: *_traditional_vocal_* token in filename."""
    name = filename.lower()
    for token in ("traditional_vocal", "pansori", "gugak"):
        if token in name:
            return "traditional_vocal" if token == "gugak" else token
    return None
