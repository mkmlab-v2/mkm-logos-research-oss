#!/usr/bin/env python3
"""
Local Stable Audio Open external generator (diffusers · B-track [HYPO]).

CLI contract matches ``external_generator_template_v1.py`` / MusicGen external path.
Default model: ``stabilityai/stable-audio-open-1.0`` (self-host weights; not Track A audio).
"""

from __future__ import annotations

import argparse
import json
import os
import wave
from pathlib import Path
from typing import Any

try:
    from scripts.audio.musicgen_external_generator_v1 import (
        _load_json,
        _post_process_loop_lufs,
        _resolve_prompt,
        _write_wav_mono_int16,
    )
except ModuleNotFoundError:
    from musicgen_external_generator_v1 import (
        _load_json,
        _post_process_loop_lufs,
        _resolve_prompt,
        _write_wav_mono_int16,
    )


def _resolve_seconds(args_seconds: float, conditioning: dict[str, Any] | None) -> float:
    cap = float(args_seconds)
    if conditioning:
        cond = conditioning.get("conditioning") or {}
        if cond.get("duration_seconds"):
            cap = min(cap, float(cond["duration_seconds"]))
    return max(1.0, min(47.0, cap))


def _hf_token() -> str | None:
    for key in ("HF_TOKEN", "HUGGINGFACE_HUB_TOKEN", "HUGGING_FACE_HUB_TOKEN"):
        val = os.environ.get(key, "").strip()
        if val:
            return val
    return None


def _generate_stable_audio(
    *,
    model_id: str,
    prompt: str,
    seconds: float,
    steps: int,
    guidance: float,
    seed: int | None,
) -> tuple[Any, int, str]:
    import numpy as np
    import torch
    from diffusers import StableAudioPipeline

    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32
    token = _hf_token()
    if token:
        try:
            from huggingface_hub import login

            login(token=token, add_to_git_credential=False)
        except Exception:
            pass
    pipe = StableAudioPipeline.from_pretrained(model_id, torch_dtype=dtype, token=token)
    pipe = pipe.to(device)

    gen = None
    if seed is not None:
        gen = torch.Generator(device=device).manual_seed(seed)

    result = pipe(
        prompt,
        audio_end_in_s=seconds,
        num_inference_steps=steps,
        guidance_scale=guidance,
        generator=gen,
    )
    audio = result.audios[0]
    if hasattr(audio, "detach"):
        audio = audio.detach().cpu().numpy()
    arr = np.asarray(audio, dtype=np.float64).reshape(-1)
    out_sr = int(getattr(pipe.vae, "sampling_rate", 44100))
    return arr, out_sr, device


def main() -> int:
    ap = argparse.ArgumentParser(description="Stable Audio Open external BGM generator (local GPU/CPU).")
    ap.add_argument("--seed-json", type=Path, required=True)
    ap.add_argument("--out-wav", type=Path, required=True)
    ap.add_argument("--index", type=int, default=0)
    ap.add_argument("--run-id", type=str, default="")
    ap.add_argument("--seconds", type=float, default=12.0)
    ap.add_argument("--sample-rate", type=int, default=32000)
    ap.add_argument("--conditioning-json", type=Path, default=None)
    ap.add_argument(
        "--model-id",
        type=str,
        default=os.environ.get("MKM_AUDIO_STABLE_AUDIO_MODEL", "stabilityai/stable-audio-open-1.0"),
    )
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not args.seed_json.is_file():
        print(json.dumps({"ok": False, "error": "seed-json missing"}))
        return 2

    seed_doc = _load_json(args.seed_json)
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
    prompt = _resolve_prompt(seed_doc, conditioning, expand)
    seconds = _resolve_seconds(args.seconds, conditioning)
    steps = int(os.environ.get("MKM_AUDIO_STABLE_AUDIO_STEPS", "100"))
    guidance = float(os.environ.get("MKM_AUDIO_STABLE_AUDIO_GUIDANCE", "7.0"))

    if args.dry_run:
        print(
            json.dumps(
                {
                    "ok": True,
                    "generator": "stable_audio_open_external_generator_v1",
                    "dry_run": True,
                    "model_id": args.model_id,
                    "prompt_preview": prompt[:200],
                    "seconds": seconds,
                    "steps": steps,
                    "guidance_scale": guidance,
                    "conditioning_json": str(cond_path) if cond_path else None,
                },
                ensure_ascii=False,
            )
        )
        return 0

    try:
        import torch  # noqa: F401
    except ImportError as exc:
        print(json.dumps({"ok": False, "error": f"missing deps: {exc}"}))
        return 3

    seed_raw = os.environ.get("MKM_AUDIO_TORCH_SEED", "").strip()
    torch_seed = int(seed_raw) if seed_raw else None

    try:
        samples, out_sr, device = _generate_stable_audio(
            model_id=args.model_id,
            prompt=prompt,
            seconds=seconds,
            steps=steps,
            guidance=guidance,
            seed=torch_seed,
        )
    except Exception as exc:
        err_name = type(exc).__name__
        hint = "Set HF_TOKEN and accept model license at huggingface.co/stabilityai/stable-audio-open-1.0"
        if "GatedRepo" in err_name or "403" in str(exc):
            print(json.dumps({"ok": False, "error": "hf_gated_model", "hint": hint, "detail": err_name}))
            return 4
        print(json.dumps({"ok": False, "error": "generation_failed", "detail": str(exc)[:500]}))
        return 5

    if out_sr != args.sample_rate:
        try:
            import numpy as np
            from scipy.signal import resample

            n_out = max(1, int(len(samples) * args.sample_rate / out_sr))
            samples = resample(samples, n_out)
            out_sr = args.sample_rate
        except ImportError:
            pass

    samples = _post_process_loop_lufs(samples, out_sr)
    _write_wav_mono_int16(args.out_wav, samples, out_sr)

    meta = {
        "provider": "local_diffusers",
        "model_id": args.model_id,
        "model_version": "diffusers_stable_audio_open",
        "commercial_terms_tag": "stable_audio_open_license_v1",
        "request_reference": args.run_id or "",
        "generator": "stable_audio_open_external_generator_v1",
        "seconds": seconds,
        "steps": steps,
        "guidance_scale": guidance,
    }
    args.out_wav.with_suffix(".meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print(
        json.dumps(
            {
                "ok": True,
                "generator": "stable_audio_open_external_generator_v1",
                "out_wav": str(args.out_wav.as_posix()),
                "model_id": args.model_id,
                "device": device,
                "prompt_preview": prompt[:200],
                "seconds": seconds,
                "sample_rate": out_sr,
                "index": args.index,
                "run_id": args.run_id,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
