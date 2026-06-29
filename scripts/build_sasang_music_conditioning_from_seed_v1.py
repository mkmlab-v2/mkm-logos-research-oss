#!/usr/bin/env python3
"""Build sasang_music_conditioning_v1 from audio_bgm_seed_v1 (+ optional lens JSON). B-track [HYPO]."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

_SASANG_TEMPO = {
    "taeyang": 108,
    "soyang": 96,
    "taeeum": 72,
    "soeum": 60,
    "soeumin": 60,
}


def _build(seed: dict[str, Any], sasang: str, *, max_duration_seconds: float) -> dict[str, Any]:
    bpm = float(seed.get("bpm") or _SASANG_TEMPO.get(sasang, 72))
    base = str(seed.get("base_prompt") or "instrumental underscore bed")
    mood = str(seed.get("mood") or "neutral")
    loop_s = float(seed.get("target_loop_seconds") or 8.0)
    duration_seconds = min(loop_s, max(1.0, max_duration_seconds))
    prompt_en = f"{base}, {mood}, {int(bpm)} bpm, sasang {sasang}, B-track research preview, no vocals"
    return {
        "schema": "sasang_music_conditioning_v1",
        "version": "1.0.0",
        "hypothesis_class": "HYPO",
        "upstream": {
            "mapping_schema": "sasang_music_mapping_v1",
            "sasang_primary": sasang,
            "gate_decision": "PASS",
        },
        "generator_target": "musicgen",
        "conditioning": {
            "prompt_en": prompt_en,
            "duration_seconds": duration_seconds,
            "sample_rate": 32000,
            "tempo_bpm_target": bpm,
        },
        "provenance": {
            "source": "adapter_from_mapping",
            "commercial_terms_tag": "apache2_self_host_weights_v1",
            "model_id_hint": "facebook/musicgen-small",
            "experiment_id": str(seed.get("seed_id") or "adapter"),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed-json", type=Path, required=True)
    ap.add_argument("--out-json", type=Path, required=True)
    ap.add_argument("--sasang-primary", type=str, default="")
    ap.add_argument(
        "--max-duration-seconds",
        type=float,
        default=0.0,
        help="Cap duration; 0 = use seed target_loop_seconds (fallback 32).",
    )
    args = ap.parse_args()
    seed = json.loads(args.seed_json.read_text(encoding="utf-8"))
    lens = seed.get("lens") or {}
    sasang = (args.sasang_primary or lens.get("sasang_bias") or "taeeum").strip().lower()
    max_duration = args.max_duration_seconds
    if max_duration <= 0:
        max_duration = float(seed.get("target_loop_seconds") or 32.0)
    doc = _build(seed, sasang, max_duration_seconds=max_duration)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.out_json), "sasang_primary": sasang}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
