#!/usr/bin/env python3
"""Build dynamic system-prompt overlay from lens music governance/emotion context (M20).

This is Level-1 prompt injection adapter (advisory, inference-time only).
User content and control parameters remain separated by contract.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GOV = ROOT / "docs" / "final" / "artifacts" / "lens_music_audition_governance_status_latest.json"
DEFAULT_CHAIN = ROOT / "reports" / "_tmp_m15_chain.json"
DEFAULT_OUT = ROOT / "reports" / "lens_music_prompt_overlay_latest.json"
DEFAULT_STATE = ROOT / "reports" / "lens_music_prompt_overlay_state_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _pick_tone(tempo_bpm: float, valence: float, state: str) -> dict[str, Any]:
    if state == "WATCH":
        return {
            "answer_style": "calm_guarded",
            "sentence_length": "short_to_medium",
            "temperature_hint": 0.45,
            "voice_hint": "stable_cautious",
        }
    energetic = tempo_bpm >= 100.0 or valence > 0.2
    if energetic:
        return {
            "answer_style": "bright_concise",
            "sentence_length": "short",
            "temperature_hint": 0.62,
            "voice_hint": "clear_energetic",
        }
    return {
        "answer_style": "empathetic_reflective",
        "sentence_length": "medium",
        "temperature_hint": 0.52,
        "voice_hint": "calm_warm",
    }


def _lookup_sasang_target_bpm(sasang_key: str) -> float:
    table = {
        "taeyang": 130.0,
        "soyang": 110.0,
        "taeeum": 70.0,
        "soeumin": 80.0,
    }
    return float(table.get((sasang_key or "").strip().lower(), 90.0))


def _apply_ema(previous: float, target: float, alpha: float) -> float:
    a = max(0.0, min(1.0, float(alpha)))
    return (a * target) + ((1.0 - a) * previous)


def build_overlay(
    governance: dict[str, Any],
    chain_doc: dict[str, Any],
    *,
    prev_state: dict[str, Any] | None = None,
    ema_alpha: float = 0.4,
) -> tuple[dict[str, Any], dict[str, Any]]:
    state = str(governance.get("state") or "UNKNOWN")
    m9 = dict(chain_doc.get("melody_stage_m9") or {})
    snapshot = dict(m9.get("input_snapshot") or {})
    raw_tempo_bpm = float(snapshot.get("tempo_target_bpm") or 90.0)
    valence = float(snapshot.get("valence") or 0.0)
    arousal = float(snapshot.get("arousal") or 0.0)
    evo = dict(chain_doc.get("emotion_va_overlay_v1") or {})
    sasang = str(evo.get("sasang_primary") or snapshot.get("sasang_primary") or "")
    target_bpm = _lookup_sasang_target_bpm(sasang)
    previous_bpm = float((prev_state or {}).get("smoothed_bpm", raw_tempo_bpm))
    smoothed_bpm = _apply_ema(previous=previous_bpm, target=target_bpm, alpha=ema_alpha)
    tempo_bpm = round((smoothed_bpm + raw_tempo_bpm) / 2.0, 3)
    style = _pick_tone(tempo_bpm=tempo_bpm, valence=valence, state=state)

    global_state = {
        "schema": "lens_music_prompt_overlay_v1",
        "generated_at_utc": _utc_now(),
        "state": state,
        "tempo_bpm": tempo_bpm,
        "valence": valence,
        "arousal": arousal,
        "sasang_primary": sasang or "unknown",
        "raw_tempo_bpm": raw_tempo_bpm,
        "target_bpm_from_sasang": target_bpm,
        "smoothed_bpm": round(smoothed_bpm, 3),
        "ema_alpha": float(ema_alpha),
        "style": style,
    }
    system_instructions = (
        f"[Global State: BPM={tempo_bpm:.1f}, Valence={valence:.3f}, Arousal={arousal:.3f}, Governance={state}]\n"
        f"- Use {style['answer_style']} tone.\n"
        f"- Keep sentence length {style['sentence_length']}.\n"
        "- Maintain factual caution when governance is WATCH.\n"
        "- Do not claim biological equivalence; describe as high-fidelity emulation only.\n"
        "- Keep control parameters separate from user message content."
    )
    overlay = {
        "schema": "lens_music_prompt_overlay_v1",
        "generated_at_utc": _utc_now(),
        "global_state": global_state,
        "system_instructions": system_instructions,
        "control_plane_contract": {
            "control_plane_user_plane_separation": True,
            "advisory_only": True,
            "no_training_side_effect": True,
        },
        "references": {
            "governance_status_schema": governance.get("schema"),
            "chain_schema": chain_doc.get("schema"),
        },
    }
    next_state = {
        "schema": "lens_music_prompt_overlay_state_v1",
        "generated_at_utc": _utc_now(),
        "smoothed_bpm": round(smoothed_bpm, 3),
        "sasang_primary": sasang or "unknown",
        "ema_alpha": float(ema_alpha),
    }
    return overlay, next_state


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--governance-json", type=Path, default=DEFAULT_GOV)
    ap.add_argument("--chain-json", type=Path, default=DEFAULT_CHAIN)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--state-json", type=Path, default=DEFAULT_STATE)
    ap.add_argument("--ema-alpha", type=float, default=0.4)
    args = ap.parse_args()

    gov = _read_json(args.governance_json)
    chain = _read_json(args.chain_json)
    prev_state = _read_json(args.state_json)
    out_doc, next_state = build_overlay(gov, chain, prev_state=prev_state, ema_alpha=float(args.ema_alpha))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.state_json.parent.mkdir(parents=True, exist_ok=True)
    args.state_json.write_text(json.dumps(next_state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(args.out.resolve()),
                "state": out_doc["global_state"]["state"],
                "smoothed_bpm": out_doc["global_state"]["smoothed_bpm"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
