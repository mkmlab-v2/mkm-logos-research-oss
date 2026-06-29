#!/usr/bin/env python3
"""AnimateDiff hypo external generator (B-track [HYPO] · research-only · not showroom LUT)."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_BASE = "runwayml/stable-diffusion-v1-5"
DEFAULT_ADAPTER = "guoyww/animatediff-motion-adapter-v1-5-2"

PROMPT_BY_PAIR: dict[tuple[str, str], str] = {
    ("soyang", "idle"): "abstract golden ambient loop, calm radial glow, soft motion, cinematic",
    ("soyang", "defend"): "guarded amber atmosphere, slow defensive pulse, abstract ambient video loop",
    ("soyang", "attack"): "warm momentum streaks, abstract energy, short ambient motion loop",
    ("taeyang", "idle"): "solar golden ambient loop, gentle radiant pulse, abstract cinematic motion",
    ("taeyang", "defend"): "sunset guard tone, amber shield glow, slow abstract loop",
    ("taeyang", "attack"): "bright solar flare motion, abstract attack energy, ambient loop",
    ("taeeum", "idle"): "cool blue-gray ambient mist, calm water-like motion, abstract loop",
    ("taeeum", "defend"): "muted teal defensive swirl, soft abstract guard loop",
    ("taeeum", "attack"): "cold wave surge, abstract blue attack motion, ambient loop",
    ("soeum", "idle"): "violet soft ambient drift, quiet abstract loop, gentle motion",
    ("soeum", "defend"): "lavender protective haze, slow guard abstract loop",
    ("soeum", "attack"): "purple pulse streaks, abstract attack ambient loop",
}


def _utc_now_z() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _hf_token() -> str | None:
    for key in ("HF_TOKEN", "HUGGINGFACE_HUB_TOKEN", "HUGGING_FACE_HUB_TOKEN"):
        val = os.environ.get(key, "").strip()
        if val:
            return val
    return None


def _resolve_prompt(sasang: str, mode: str, override: str) -> str:
    if override.strip():
        return override.strip()
    key = (sasang.strip().lower(), mode.strip().lower())
    return PROMPT_BY_PAIR.get(key, f"abstract ambient {sasang} {mode} motion loop, cinematic")


def _ffmpeg_webm_from_frames(frame_dir: Path, out_webm: Path, *, fps: int, bitrate_k: int) -> int:
    if shutil.which("ffmpeg") is None:
        print("[animatediff-hypo] ffmpeg not found", file=sys.stderr)
        return 2
    pattern = str(frame_dir / "frame_%04d.png")
    cmd = [
        "ffmpeg",
        "-y",
        "-framerate",
        str(fps),
        "-i",
        pattern,
        "-an",
        "-c:v",
        "libvpx-vp9",
        "-b:v",
        f"{bitrate_k}k",
        "-pix_fmt",
        "yuv420p",
        str(out_webm),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        print((proc.stderr or "")[-800:], file=sys.stderr)
    return proc.returncode


def _blend_pil_frames(
    ai_frames: list,
    *,
    sasang: str,
    mode: str,
    width: int,
    height: int,
    blend: float,
) -> list:
    from PIL import Image

    from scripts.build_lens_btrack_video_loops_v1 import _render_animated_frame

    out: list[Image.Image] = []
    n = len(ai_frames)
    for i, frame in enumerate(ai_frames):
        if isinstance(frame, Image.Image):
            ai_img = frame.convert("RGB")
        else:
            ai_img = Image.fromarray(frame).convert("RGB")
        pil_img = _render_animated_frame(
            frame_idx=i,
            total_frames=n,
            mode=mode,
            sasang=sasang,
            width=width,
            height=height,
        )
        if pil_img.mode != "RGB":
            pil_img = pil_img.convert("RGB")
        alpha = max(0.0, min(1.0, blend))
        out.append(Image.blend(ai_img, pil_img, alpha))
    return out


def _generate_frames(
    *,
    prompt: str,
    frame_dir: Path,
    num_frames: int,
    width: int,
    height: int,
    steps: int,
    guidance: float,
    seed: int,
    base_model: str,
    adapter_model: str,
    sasang: str,
    mode: str,
    pil_hybrid: bool,
    pil_hybrid_blend: float,
) -> dict[str, Any]:
    import torch
    from diffusers import AnimateDiffPipeline, MotionAdapter, DDIMScheduler
    from PIL import Image

    token = _hf_token()
    adapter = MotionAdapter.from_pretrained(adapter_model, torch_dtype=torch.float16, token=token)
    pipe = AnimateDiffPipeline.from_pretrained(
        base_model,
        motion_adapter=adapter,
        torch_dtype=torch.float16,
        token=token,
    )
    pipe.scheduler = DDIMScheduler.from_config(pipe.scheduler.config)
    pipe.enable_vae_slicing()
    if torch.cuda.is_available():
        pipe.enable_model_cpu_offload()
    else:
        pipe = pipe.to("cpu")

    gen = torch.Generator(device="cpu").manual_seed(seed)
    out = pipe(
        prompt=prompt,
        num_frames=num_frames,
        width=width,
        height=height,
        num_inference_steps=steps,
        guidance_scale=guidance,
        generator=gen,
    )
    frames = list(out.frames[0])
    if pil_hybrid:
        frames = _blend_pil_frames(
            frames,
            sasang=sasang,
            mode=mode,
            width=width,
            height=height,
            blend=pil_hybrid_blend,
        )
    frame_dir.mkdir(parents=True, exist_ok=True)
    for i, frame in enumerate(frames):
        if isinstance(frame, Image.Image):
            img = frame
        else:
            img = Image.fromarray(frame)
        img.save(frame_dir / f"frame_{i:04d}.png", format="PNG")
    return {
        "num_frames_written": len(frames),
        "device": "cuda" if torch.cuda.is_available() else "cpu",
        "pil_hybrid": pil_hybrid,
        "pil_hybrid_blend": pil_hybrid_blend if pil_hybrid else None,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sasang", default="taeyang")
    ap.add_argument("--mode", default="idle")
    ap.add_argument("--prompt", default="")
    ap.add_argument("--out-webm", type=Path, required=True)
    ap.add_argument("--num-frames", type=int, default=8)
    ap.add_argument("--width", type=int, default=256)
    ap.add_argument("--height", type=int, default=144)
    ap.add_argument("--steps", type=int, default=8)
    ap.add_argument("--guidance", type=float, default=7.5)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--fps", type=int, default=8)
    ap.add_argument("--bitrate-k", type=int, default=600)
    ap.add_argument("--base-model", default=DEFAULT_BASE)
    ap.add_argument("--adapter-model", default=DEFAULT_ADAPTER)
    ap.add_argument(
        "--pil-hybrid",
        action="store_true",
        help="Blend PIL animated frames (brand LUT colors) into AI frames",
    )
    ap.add_argument(
        "--pil-hybrid-blend",
        type=float,
        default=0.55,
        help="PIL weight in blend (0=AI only, 1=PIL only); recommended 0.55",
    )
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--report-json", type=Path, default=None)
    args = ap.parse_args()

    prompt = _resolve_prompt(args.sasang, args.mode, args.prompt)
    report: dict[str, Any] = {
        "schema": "animatediff_hypo_external_generator_v1",
        "hypothesis_class": "HYPO",
        "research_only": True,
        "generated_at_utc": _utc_now_z(),
        "sasang_primary": args.sasang,
        "showroom_display_mode": args.mode,
        "prompt": prompt,
        "out_webm": str(args.out_webm),
        "num_frames": args.num_frames,
        "width": args.width,
        "height": args.height,
        "steps": args.steps,
        "base_model": args.base_model,
        "adapter_model": args.adapter_model,
        "status": "pending",
    }

    if args.dry_run:
        report["status"] = "dry_run"
        if args.report_json:
            args.report_json.parent.mkdir(parents=True, exist_ok=True)
            args.report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False))
        return 0

    try:
        with tempfile.TemporaryDirectory(prefix="animatediff_hypo_") as tmp:
            frame_dir = Path(tmp)
            meta = _generate_frames(
                prompt=prompt,
                frame_dir=frame_dir,
                num_frames=args.num_frames,
                width=args.width,
                height=args.height,
                steps=args.steps,
                guidance=args.guidance,
                seed=args.seed,
                base_model=args.base_model,
                adapter_model=args.adapter_model,
                sasang=args.sasang,
                mode=args.mode,
                pil_hybrid=bool(args.pil_hybrid),
                pil_hybrid_blend=float(args.pil_hybrid_blend),
            )
            report.update(meta)
            report["pil_hybrid"] = bool(args.pil_hybrid)
            args.out_webm.parent.mkdir(parents=True, exist_ok=True)
            ff = _ffmpeg_webm_from_frames(
                frame_dir, args.out_webm, fps=args.fps, bitrate_k=args.bitrate_k
            )
            report["ffmpeg_exit"] = ff
            report["webm_ok"] = args.out_webm.is_file() and args.out_webm.stat().st_size > 0
            report["status"] = "ok" if report["webm_ok"] and ff == 0 else "fail"
    except Exception as exc:
        report["status"] = "fail"
        report["error"] = str(exc)
        if args.report_json:
            args.report_json.parent.mkdir(parents=True, exist_ok=True)
            args.report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"[animatediff-hypo] FAIL: {exc}", file=sys.stderr)
        return 1

    if args.report_json:
        args.report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
