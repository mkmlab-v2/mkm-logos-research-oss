#!/usr/bin/env python3
"""
Dynamic BGM conditioning diff stub (B-track [HYPO]).

Maps runtime game/session state (hp_pct, sasang) to a conditioning patch for
sasang_music_conditioning_v1 — Track C demo / research only.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

_SASANG_TEMPO = {
    "taeyang": 108,
    "soyang": 96,
    "taeeum": 72,
    "soeumin": 60,
}

_MOOD_BY_HP = (
    (0.25, "urgent"),
    (0.55, "tense"),
    (0.80, "neutral"),
    (1.01, "calm"),
)


try:
    from scripts.audio.musicgen_numeric_conditioning_v1 import clamp_tempo_for_lens_gate
except ModuleNotFoundError:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from scripts.audio.musicgen_numeric_conditioning_v1 import clamp_tempo_for_lens_gate


def _mood_for_hp(hp_pct: float) -> str:
    for threshold, mood in _MOOD_BY_HP:
        if hp_pct <= threshold:
            return mood
    return "urgent"


def _replace_bpm_in_prompt(prompt: str, bpm: int) -> str:
    if re.search(r"\b\d+\s*bpm\b", prompt, flags=re.I):
        return re.sub(r"\b\d+\s*bpm\b", f"{bpm} bpm", prompt, count=1, flags=re.I)
    return f"{prompt}, {bpm} bpm"


def _normalize_sasang_in_prompt(prompt: str, sasang_key: str) -> str:
    """Keep a single sasang token (avoids seed-bias + matrix sasang duplication)."""
    cleaned = re.sub(r",?\s*sasang\s+\w+", "", prompt, flags=re.I)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip().strip(",").strip()
    return f"{cleaned}, sasang {sasang_key}"


def _strip_sasang_from_prompt(prompt: str) -> str:
    cleaned = re.sub(r",?\s*sasang\s+\w+", "", prompt, flags=re.I)
    return re.sub(r"\s{2,}", " ", cleaned).strip().strip(",").strip()


_ALLOWED_LENS_COUNTS = frozenset({0, 1, 3})


def build_dynamic_diff(
    *,
    base_conditioning: dict[str, Any],
    hp_pct: float,
    sasang: str | None = None,
    lens_count: int = 1,
) -> dict[str, Any]:
    if base_conditioning.get("schema") != "sasang_music_conditioning_v1":
        raise ValueError("base must be sasang_music_conditioning_v1")
    if int(lens_count) not in _ALLOWED_LENS_COUNTS:
        raise ValueError(f"lens_count must be one of {sorted(_ALLOWED_LENS_COUNTS)}; got {lens_count!r}")

    lens_count = int(lens_count)
    hp = max(0.0, min(1.0, float(hp_pct)))
    cond = dict(base_conditioning.get("conditioning") or {})
    upstream = dict(base_conditioning.get("upstream") or {})
    sasang_key = (sasang or upstream.get("sasang_primary") or "taeeum").strip().lower()
    if sasang_key not in _SASANG_TEMPO:
        sasang_key = "taeeum"

    base_bpm = float(cond.get("tempo_bpm_target") or _SASANG_TEMPO[sasang_key])
    sasang_bpm = float(_SASANG_TEMPO[sasang_key])
    urgency_boost = 1.0 + 0.12 * (1.0 - hp)
    if lens_count == 0:
        tempo_blend = base_bpm * (1.0 - 0.2 * hp)
    else:
        tempo_blend = base_bpm * (1.0 - 0.35 * hp) + sasang_bpm * (0.35 * hp)
    target_bpm_raw = round(max(40.0, min(200.0, tempo_blend * urgency_boost)), 2)
    if lens_count >= 3:
        target_bpm_raw = round(target_bpm_raw * 1.02, 2)
    target_bpm, lens_clamp_meta = clamp_tempo_for_lens_gate(target_bpm_raw)

    base_velocity = float(cond.get("velocity_0_1") if cond.get("velocity_0_1") is not None else 0.45)
    velocity = round(max(0.15, min(1.0, base_velocity * (0.55 + 0.75 * (1.0 - hp)))), 3)
    if lens_count >= 3:
        velocity = round(max(0.15, min(1.0, velocity * 0.95)), 3)
    mood = _mood_for_hp(hp)

    prompt = str(cond.get("prompt_en") or "instrumental underscore bed, no vocals")
    prompt = re.sub(r"\b(calm|neutral|tense|urgent)(?:_\w+)?\b", mood, prompt, count=1, flags=re.I)
    if mood not in prompt.lower():
        prompt = f"{prompt}, {mood}"
    prompt = _replace_bpm_in_prompt(prompt, int(round(target_bpm)))
    if lens_count == 0:
        prompt = _strip_sasang_from_prompt(prompt)
    else:
        prompt = _normalize_sasang_in_prompt(prompt, sasang_key)
    if lens_count >= 3:
        prompt = f"{prompt}, logos_non_gating_shadow"

    patch = {
        "tempo_bpm_target": target_bpm,
        "velocity_0_1": velocity,
        "prompt_en": prompt,
    }

    active_lenses: list[str] = []
    if lens_count == 0:
        active_lenses = []
    elif lens_count == 1:
        active_lenses = ["sasang"]
    else:
        active_lenses = ["sasang", "myeongni", "logos"]

    return {
        "schema": "dynamic_bgm_conditioning_diff_v1",
        "version": "1.1.0",
        "hypothesis_class": "HYPO",
        "inputs": {
            "hp_pct": hp,
            "sasang": sasang_key if lens_count > 0 else None,
            "mood": mood,
            "lens_count": lens_count,
            "active_lenses": active_lenses,
        },
        "base_conditioning_path_hint": base_conditioning.get("provenance", {}).get("experiment_id"),
        "suggested_conditioning_patch": patch,
        "lens_safe_tempo_clamp": lens_clamp_meta,
        "notes": "Track C demo stub — not live game wiring; no clinical efficacy claim.",
    }


def apply_patch_to_conditioning(base: dict[str, Any], diff: dict[str, Any]) -> dict[str, Any]:
    merged = json.loads(json.dumps(base))
    patch = diff.get("suggested_conditioning_patch") or {}
    cond = merged.setdefault("conditioning", {})
    for key, val in patch.items():
        cond[key] = val
    inputs = diff.get("inputs") or {}
    upstream = merged.setdefault("upstream", {})
    if inputs.get("sasang"):
        upstream["sasang_primary"] = inputs.get("sasang")
    upstream["lens_count"] = inputs.get("lens_count")
    upstream["active_lenses"] = inputs.get("active_lenses")
    exp = str(merged.get("provenance", {}).get("experiment_id") or "dynamic")
    lc = inputs.get("lens_count", 1)
    merged.setdefault("provenance", {})["experiment_id"] = (
        f"{exp}_hp{int(float(inputs.get('hp_pct', 0)) * 100):03d}_lc{lc}"
    )
    merged["notes"] = (
        f"dynamic_bgm: hp_pct={inputs.get('hp_pct')} lens_count={lc} mood patch"
    )
    return merged


def main() -> int:
    ap = argparse.ArgumentParser(description="Build dynamic BGM conditioning diff from hp_pct + sasang.")
    ap.add_argument("--base-conditioning-json", type=Path, required=True)
    ap.add_argument("--hp-pct", type=float, required=True, help="0=low HP/tense, 1=full HP/calm")
    ap.add_argument("--sasang", type=str, default="")
    ap.add_argument("--lens-count", type=int, default=1, choices=sorted(_ALLOWED_LENS_COUNTS))
    ap.add_argument("--out-json", type=Path, required=True)
    ap.add_argument("--apply-out-json", type=Path, default=None, help="Optional merged conditioning output.")
    args = ap.parse_args()

    base = json.loads(args.base_conditioning_json.read_text(encoding="utf-8"))
    diff = build_dynamic_diff(
        base_conditioning=base,
        hp_pct=args.hp_pct,
        sasang=args.sasang or None,
        lens_count=args.lens_count,
    )
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(diff, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.apply_out_json:
        merged = apply_patch_to_conditioning(base, diff)
        args.apply_out_json.parent.mkdir(parents=True, exist_ok=True)
        args.apply_out_json.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"ok": True, "out": str(args.out_json), "target_bpm": diff["suggested_conditioning_patch"]["tempo_bpm_target"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
