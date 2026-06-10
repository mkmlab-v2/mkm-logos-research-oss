#!/usr/bin/env python3
"""
Local MusicGen external generator (transformers · B-track [HYPO]).

CLI contract matches `external_generator_template_v1.py` / `run_bgm_generation_batch.py --emit external`.

Reads:
  - ``--seed-json`` (audio_bgm_seed_v1)
  - optional ``--conditioning-json`` or env ``MKM_AUDIO_CONDITIONING_JSON``
  - optional expand sidecar ``{out_wav_stem}.expand.json`` (Gemini chain)

Requires: torch, transformers, scipy (or soundfile). Default model: facebook/musicgen-small.
First run downloads weights (~1.5GB). Not Track A commercial audio.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import wave
from pathlib import Path
from typing import Any

try:
    from scripts.audio.musicgen_numeric_conditioning_v1 import (
        build_melody_guide_mono,
        extract_numeric_conditioning,
        guidance_scale_from_velocity,
        resolve_melody_model_id,
        time_stretch_to_target_bpm,
    )
except ModuleNotFoundError:
    from musicgen_numeric_conditioning_v1 import (
        build_melody_guide_mono,
        extract_numeric_conditioning,
        guidance_scale_from_velocity,
        resolve_melody_model_id,
        time_stretch_to_target_bpm,
    )


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_prompt(seed: dict[str, Any], conditioning: dict[str, Any] | None, expand: dict[str, Any] | None) -> str:
    if conditioning:
        cond = conditioning.get("conditioning") or {}
        if cond.get("prompt_en"):
            return str(cond["prompt_en"])
    if expand:
        for key in ("expanded_prompt_en", "expanded_prompt_ko"):
            if expand.get(key):
                return str(expand[key])
    base = str(seed.get("base_prompt") or "").strip()
    bpm = seed.get("bpm")
    mood = seed.get("mood") or ""
    lens = seed.get("lens") or {}
    sasang = lens.get("sasang_bias") or ""
    parts = [p for p in [base, f"{mood} mood" if mood else "", f"{bpm}bpm" if bpm else "", f"sasang {sasang}" if sasang else ""] if p]
    return ", ".join(parts) if parts else "minimal instrumental underscore bed, no vocals"


def _resolve_effective_seconds(
    seed: dict[str, Any],
    conditioning: dict[str, Any] | None,
    cli_seconds: float,
) -> float:
    """Seed target_loop_seconds > conditioning duration > CLI --seconds."""
    numeric = extract_numeric_conditioning(conditioning)
    if numeric.get("duration_seconds") is not None:
        return float(numeric["duration_seconds"])
    loop_s = seed.get("target_loop_seconds")
    if loop_s is not None:
        return float(loop_s)
    if cli_seconds and cli_seconds > 0:
        return float(cli_seconds)
    return 8.0


def _enrich_numeric_duration(numeric: dict[str, Any], effective_seconds: float) -> dict[str, Any]:
    if numeric.get("duration_seconds") is not None:
        return numeric
    return {**numeric, "duration_seconds": float(effective_seconds)}


def _resolve_max_new_tokens(seconds: float, conditioning: dict[str, Any] | None) -> int:
    cap = float(seconds)
    if conditioning:
        cond = conditioning.get("conditioning") or {}
        if cond.get("duration_seconds"):
            cap = min(cap, float(cond["duration_seconds"]))
    tokens_per_second = float(os.environ.get("MKM_AUDIO_MUSICGEN_TOKENS_PER_SECOND", "51"))
    max_cap = int(os.environ.get("MKM_AUDIO_MUSICGEN_MAX_NEW_TOKENS", "2048"))
    min_floor = int(os.environ.get("MKM_AUDIO_MUSICGEN_MIN_NEW_TOKENS", "128"))
    return max(min_floor, min(max_cap, int(math.ceil(cap * tokens_per_second))))


def _post_process_loop_lufs(samples, sample_rate: int, *, target_lufs: float = -12.0):
    import numpy as np

    arr = np.asarray(samples, dtype=np.float64).reshape(-1)
    window = 2048
    try:
        import pyloudnorm as pyln  # type: ignore

        meter = pyln.Meter(sample_rate)

        def _normalize_to_target(signal: np.ndarray) -> np.ndarray:
            loudness = float(meter.integrated_loudness(signal.reshape(-1, 1)))
            if loudness <= -70.0:
                return signal
            if abs(loudness - target_lufs) <= 0.75:
                return signal
            return pyln.normalize.loudness(signal.reshape(-1, 1), loudness, target_lufs).reshape(-1)

        arr = _normalize_to_target(arr)
    except ImportError:
        peak = float(np.max(np.abs(arr))) or 1.0
        if peak > 0.01:
            arr = arr * min(1.0, 0.89 / peak)

    fade_n = max(2, int(0.03 * sample_rate))
    if len(arr) > fade_n * 2:
        ramp = np.linspace(0.0, 1.0, fade_n)
        arr[:fade_n] *= ramp
        arr[-fade_n:] *= ramp[::-1]
    if len(arr) > window * 2:
        head = arr[:window].copy()
        arr[-window:] = head
        arr[-1] = arr[0]

    try:
        import pyloudnorm as pyln  # type: ignore

        meter = pyln.Meter(sample_rate)
        loudness = float(meter.integrated_loudness(arr.reshape(-1, 1)))
        if loudness > -70.0 and abs(loudness - (-14.0)) > 0.75:
            arr = pyln.normalize.loudness(arr.reshape(-1, 1), loudness, -14.0).reshape(-1)
    except ImportError:
        pass
    return arr


def _ensure_target_duration(samples, sample_rate: int, target_seconds: float | None):
    """Pad loop to target clip length when BPM stretch shortens below hub minimum."""
    import numpy as np

    if not target_seconds or target_seconds <= 0:
        return samples
    arr = np.asarray(samples, dtype=np.float32).reshape(-1)
    target_len = max(128, int(float(target_seconds) * int(sample_rate)))
    if len(arr) >= target_len:
        return arr[:target_len]
    if len(arr) < 128:
        return arr
    tile = arr.copy()
    out = tile
    while len(out) < target_len:
        need = target_len - len(out)
        out = np.concatenate([out, tile[: min(len(tile), need)]])
    return out[:target_len]


def _truthy_env(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _numeric_injection_mode(numeric: dict[str, Any]) -> str:
    """melody | stretch | off"""
    mode = os.environ.get("MKM_AUDIO_MUSICGEN_NUMERIC_MODE", "").strip().lower()
    if mode in {"melody", "stretch", "off"}:
        return mode
    if not numeric.get("tempo_bpm_target"):
        return "off"
    if _truthy_env("MKM_AUDIO_MUSICGEN_NUMERIC_OFF"):
        return "off"
    if _truthy_env("MKM_AUDIO_MUSICGEN_MELODY_GUIDE") or mode == "melody":
        return "melody"
    if mode == "stretch":
        return "stretch"
    return "off"


def _load_model_bundle(
    *,
    model_id: str,
    numeric_mode: str,
    numeric: dict[str, Any],
    sample_rate_hint: int,
) -> tuple[Any, Any, str, str, bool]:
    """Load processor+model once for warm batch sessions."""
    import torch

    device = "cuda" if torch.cuda.is_available() else "cpu"
    use_melody = numeric_mode == "melody" and bool(numeric.get("tempo_bpm_target"))
    dtype = torch.float32 if use_melody else (torch.float16 if device == "cuda" else torch.float32)
    effective_model = resolve_melody_model_id(model_id) if use_melody else model_id

    if use_melody:
        from transformers import AutoProcessor, MusicgenMelodyForConditionalGeneration

        processor = AutoProcessor.from_pretrained(effective_model)
        model = MusicgenMelodyForConditionalGeneration.from_pretrained(effective_model, torch_dtype=dtype)
    else:
        from transformers import AutoProcessor, MusicgenForConditionalGeneration

        processor = AutoProcessor.from_pretrained(effective_model)
        model = MusicgenForConditionalGeneration.from_pretrained(effective_model, torch_dtype=dtype)

    model.to(device)
    model.eval()
    return processor, model, device, effective_model, use_melody


def _generate_with_bundle(
    bundle: tuple[Any, Any, str, str, bool],
    *,
    prompt: str,
    max_new_tokens: int,
    numeric: dict[str, Any],
    numeric_mode: str,
    melody_guide_seconds: float,
    sample_rate_hint: int,
) -> tuple[Any, int, str, dict[str, Any]]:
    processor, model, device, effective_model, use_melody = bundle
    guidance = guidance_scale_from_velocity(numeric.get("velocity_0_1"))
    gen_kwargs: dict[str, Any] = {"max_new_tokens": max_new_tokens, "do_sample": True, "guidance_scale": guidance}

    if use_melody:
        guide = build_melody_guide_mono(
            tempo_bpm=float(numeric["tempo_bpm_target"]),
            duration_seconds=melody_guide_seconds,
            sample_rate=sample_rate_hint,
            root_pc=int(numeric["root_pc"]) if numeric.get("root_pc") is not None else None,
            velocity_0_1=float(numeric["velocity_0_1"]) if numeric.get("velocity_0_1") is not None else None,
        )
        inputs = processor(
            audio=guide,
            sampling_rate=sample_rate_hint,
            text=[prompt],
            padding=True,
            return_tensors="pt",
        )
    else:
        inputs = processor(text=[prompt], padding=True, return_tensors="pt")

    inputs = {k: v.to(device) for k, v in inputs.items()}
    with __import__("torch").no_grad():
        audio_values = model.generate(**inputs, **gen_kwargs)

    out_sr = int(sample_rate_hint)
    if hasattr(model.config, "audio_encoder") and hasattr(model.config.audio_encoder, "sampling_rate"):
        out_sr = int(model.config.audio_encoder.sampling_rate)

    samples = audio_values[0, 0].detach().cpu().float().numpy()
    injection_meta = {
        "numeric_mode": numeric_mode,
        "model_id_effective": effective_model,
        "guidance_scale": guidance,
        "numeric_fields": numeric,
    }
    if use_melody:
        injection_meta["melody_guide_seconds"] = melody_guide_seconds
        injection_meta["melody_guide_sample_rate"] = sample_rate_hint

    if numeric.get("tempo_bpm_target") and (
        numeric_mode == "stretch"
        or (numeric_mode == "melody" and not _truthy_env("MKM_AUDIO_MUSICGEN_MELODY_NO_STRETCH"))
    ):
        import numpy as np

        samples, stretch_meta = time_stretch_to_target_bpm(
            np.asarray(samples, dtype=np.float32),
            out_sr,
            float(numeric["tempo_bpm_target"]),
        )
        injection_meta["bpm_stretch"] = stretch_meta

    target_seconds = numeric.get("duration_seconds")
    if target_seconds:
        import numpy as np

        before_len = int(np.asarray(samples).reshape(-1).shape[0])
        samples = _ensure_target_duration(samples, out_sr, float(target_seconds))
        after_len = int(np.asarray(samples).reshape(-1).shape[0])
        if after_len > before_len:
            injection_meta["duration_pad"] = {
                "target_seconds": float(target_seconds),
                "samples_before": before_len,
                "samples_after": after_len,
            }

    return samples, out_sr, device, injection_meta


def _generate_audio(
    *,
    model_id: str,
    prompt: str,
    max_new_tokens: int,
    numeric: dict[str, Any],
    numeric_mode: str,
    melody_guide_seconds: float,
    sample_rate_hint: int,
):
    bundle = _load_model_bundle(
        model_id=model_id,
        numeric_mode=numeric_mode,
        numeric=numeric,
        sample_rate_hint=sample_rate_hint,
    )
    samples, out_sr, device, injection_meta = _generate_with_bundle(
        bundle,
        prompt=prompt,
        max_new_tokens=max_new_tokens,
        numeric=numeric,
        numeric_mode=numeric_mode,
        melody_guide_seconds=melody_guide_seconds,
        sample_rate_hint=sample_rate_hint,
    )
    return samples, out_sr, device, injection_meta


class MusicGenWarmSession:
    """Keep MusicGen weights on GPU across multiple lens pair generations."""

    def __init__(self, *, model_id: str | None = None, numeric_mode: str = "melody") -> None:
        self.model_id = model_id or os.environ.get("MKM_AUDIO_MUSICGEN_MODEL", "facebook/musicgen-small")
        self.numeric_mode = numeric_mode
        self._bundle: tuple[Any, Any, str, str, bool] | None = None
        self._bundle_key: tuple[str, str] | None = None

    def _bundle_for(self, numeric: dict[str, Any], numeric_mode: str, sample_rate_hint: int):
        mode = numeric_mode or _numeric_injection_mode(numeric)
        key = (resolve_melody_model_id(self.model_id) if mode == "melody" else self.model_id, mode)
        if self._bundle is None or self._bundle_key != key:
            self._bundle = _load_model_bundle(
                model_id=self.model_id,
                numeric_mode=mode,
                numeric=numeric,
                sample_rate_hint=sample_rate_hint,
            )
            self._bundle_key = key
        return self._bundle, mode

    def generate_to_file(
        self,
        *,
        seed: dict[str, Any],
        conditioning: dict[str, Any] | None,
        out_wav: Path,
        seconds: float,
        run_id: str,
        sample_rate: int = 32000,
    ) -> dict[str, Any]:
        expand_path = out_wav.with_suffix(".expand.json")
        expand = _load_json(expand_path) if expand_path.is_file() else None
        effective_seconds = _resolve_effective_seconds(seed, conditioning, seconds)
        prompt = _resolve_prompt(seed, conditioning, expand)
        max_new_tokens = _resolve_max_new_tokens(effective_seconds, conditioning)
        numeric = _enrich_numeric_duration(
            extract_numeric_conditioning(conditioning),
            effective_seconds,
        )
        bundle, numeric_mode = self._bundle_for(numeric, self.numeric_mode, sample_rate)
        sr_hint = int(numeric.get("sample_rate") or sample_rate)
        melody_guide_seconds = min(
            float(numeric.get("duration_seconds") or effective_seconds),
            float(os.environ.get("MKM_AUDIO_MUSICGEN_MELODY_GUIDE_SECONDS", "32")),
        )
        samples, out_sr, device, injection_meta = _generate_with_bundle(
            bundle,
            prompt=prompt,
            max_new_tokens=max_new_tokens,
            numeric=numeric,
            numeric_mode=numeric_mode,
            melody_guide_seconds=melody_guide_seconds,
            sample_rate_hint=sr_hint,
        )
        samples = _post_process_loop_lufs(samples, out_sr)
        out_wav.parent.mkdir(parents=True, exist_ok=True)
        _write_wav_mono_int16(out_wav, samples, out_sr)
        meta = {
            "provider": "local_transformers",
            "model_id": injection_meta.get("model_id_effective") or self.model_id,
            "model_version": "transformers_musicgen",
            "commercial_terms_tag": "apache2_self_host_weights_v1",
            "request_reference": run_id or "",
            "generator": "musicgen_warm_session_v1",
            "numeric_injection": injection_meta,
        }
        out_wav.with_suffix(".meta.json").write_text(
            json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        return {
            "ok": True,
            "out_wav": str(out_wav.as_posix()),
            "device": device,
            "prompt_preview": prompt[:200],
            "numeric_mode": numeric_mode,
        }


def _write_wav_mono_int16(path: Path, samples, sample_rate: int) -> None:
    import numpy as np

    arr = np.asarray(samples, dtype=np.float32)
    if arr.ndim > 1:
        arr = arr.mean(axis=0)
    try:
        import pyloudnorm as pyln  # type: ignore

        meter = pyln.Meter(sample_rate)
        for _ in range(4):
            sim = np.clip(arr, -1.0, 1.0)
            loudness = float(meter.integrated_loudness(sim.reshape(-1, 1)))
            if abs(loudness - (-14.0)) <= 0.95:
                arr = sim
                break
            arr = pyln.normalize.loudness(sim.reshape(-1, 1), loudness, -14.0).reshape(-1).astype(np.float32)
    except ImportError:
        pass
    pcm = (np.clip(arr, -1.0, 1.0) * 32767.0).astype(np.int16)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm.tobytes())


def main() -> int:
    ap = argparse.ArgumentParser(description="MusicGen external BGM generator (local GPU/CPU).")
    ap.add_argument("--seed-json", type=Path, required=True)
    ap.add_argument("--out-wav", type=Path, required=True)
    ap.add_argument("--index", type=int, default=0)
    ap.add_argument("--run-id", type=str, default="")
    ap.add_argument("--seconds", type=float, default=8.0)
    ap.add_argument("--sample-rate", type=int, default=32000)
    ap.add_argument("--conditioning-json", type=Path, default=None)
    ap.add_argument("--model-id", type=str, default=os.environ.get("MKM_AUDIO_MUSICGEN_MODEL", "facebook/musicgen-small"))
    ap.add_argument("--dry-run", action="store_true", help="Skip model load; write metadata JSON only.")
    args = ap.parse_args()

    if not args.seed_json.is_file():
        print(json.dumps({"ok": False, "error": "seed-json missing"}))
        return 2

    seed = _load_json(args.seed_json)
    cond_path = args.conditioning_json
    if cond_path is None:
        env_c = os.environ.get("MKM_AUDIO_CONDITIONING_JSON", "").strip()
        if env_c:
            cond_path = Path(env_c)
        elif args.out_wav.with_suffix(".conditioning.json").is_file():
            cond_path = args.out_wav.with_suffix(".conditioning.json")

    conditioning = _load_json(cond_path) if cond_path and cond_path.is_file() else None
    expand_path = args.out_wav.with_suffix(".expand.json")
    expand = _load_json(expand_path) if expand_path.is_file() else None

    effective_seconds = _resolve_effective_seconds(seed, conditioning, args.seconds)
    prompt = _resolve_prompt(seed, conditioning, expand)
    max_new_tokens = _resolve_max_new_tokens(effective_seconds, conditioning)
    numeric = _enrich_numeric_duration(
        extract_numeric_conditioning(conditioning),
        effective_seconds,
    )
    numeric_mode = _numeric_injection_mode(numeric)
    sr_hint = int(numeric.get("sample_rate") or args.sample_rate)
    melody_guide_seconds = min(
        float(numeric.get("duration_seconds") or effective_seconds),
        float(os.environ.get("MKM_AUDIO_MUSICGEN_MELODY_GUIDE_SECONDS", "32")),
    )

    if args.dry_run:
        effective_model = resolve_melody_model_id(args.model_id) if numeric_mode == "melody" else args.model_id
        print(
            json.dumps(
                {
                    "ok": True,
                    "generator": "musicgen_external_generator_v1",
                    "dry_run": True,
                    "model_id": args.model_id,
                    "model_id_effective": effective_model,
                    "prompt_preview": prompt[:200],
                    "max_new_tokens": max_new_tokens,
                    "effective_seconds": effective_seconds,
                    "conditioning_json": str(cond_path) if cond_path else None,
                    "numeric_mode": numeric_mode,
                    "numeric_fields": numeric,
                    "guidance_scale": guidance_scale_from_velocity(numeric.get("velocity_0_1")),
                },
                ensure_ascii=False,
            )
        )
        return 0

    try:
        import torch
    except ImportError as exc:
        print(json.dumps({"ok": False, "error": f"missing deps: {exc}"}))
        return 3

    seed_raw = os.environ.get("MKM_AUDIO_TORCH_SEED", "").strip()
    if seed_raw:
        torch.manual_seed(int(seed_raw))
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(int(seed_raw))

    samples, out_sr, device, injection_meta = _generate_audio(
        model_id=args.model_id,
        prompt=prompt,
        max_new_tokens=max_new_tokens,
        numeric=numeric,
        numeric_mode=numeric_mode,
        melody_guide_seconds=melody_guide_seconds,
        sample_rate_hint=sr_hint,
    )
    samples = _post_process_loop_lufs(samples, out_sr)
    _write_wav_mono_int16(args.out_wav, samples, out_sr)

    meta = {
        "provider": "local_transformers",
        "model_id": injection_meta.get("model_id_effective") or args.model_id,
        "model_version": "transformers_musicgen",
        "commercial_terms_tag": "apache2_self_host_weights_v1",
        "request_reference": args.run_id or "",
        "generator": "musicgen_external_generator_v1",
        "numeric_injection": injection_meta,
    }
    args.out_wav.with_suffix(".meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print(
        json.dumps(
            {
                "ok": True,
                "generator": "musicgen_external_generator_v1",
                "out_wav": str(args.out_wav.as_posix()),
                "model_id": meta["model_id"],
                "device": device,
                "prompt_preview": prompt[:200],
                "max_new_tokens": max_new_tokens,
                "effective_seconds": effective_seconds,
                "sample_rate": out_sr,
                "index": args.index,
                "run_id": args.run_id,
                "conditioning_schema": (conditioning or {}).get("schema"),
                "numeric_mode": numeric_mode,
                "numeric_injection": injection_meta,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
