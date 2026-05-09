#!/usr/bin/env python3
"""Generate Veo clips from director shot plan with chained exports."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

from google import genai
from google.genai import types


def run(cmd: list[str]) -> None:
    p = subprocess.run(cmd, text=True, capture_output=True)
    if p.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{p.stderr[-1200:]}")


def export_frames(clip_path: Path, first_frame: Path, last_frame: Path) -> None:
    first_frame.parent.mkdir(parents=True, exist_ok=True)
    last_frame.parent.mkdir(parents=True, exist_ok=True)
    run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(clip_path),
            "-frames:v",
            "1",
            str(first_frame),
        ]
    )
    run(
        [
            "ffmpeg",
            "-y",
            "-sseof",
            "-0.05",
            "-i",
            str(clip_path),
            "-frames:v",
            "1",
            str(last_frame),
        ]
    )


def load_image_bytes(path: Path) -> bytes:
    data = path.read_bytes()
    if not data:
        raise RuntimeError(f"Empty image file: {path}")
    return data


def guess_mime(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in (".jpg", ".jpeg"):
        return "image/jpeg"
    return "image/png"


def extract_subject_refs_from_clip(clip_path: Path, refs_dir: Path) -> list[Path]:
    refs_dir.mkdir(parents=True, exist_ok=True)
    out: list[Path] = []
    stamps = [0.2, 2.8, 5.4]
    for i, ts in enumerate(stamps, start=1):
        p = refs_dir / f"subject_auto_{i:02d}.png"
        run(
            [
                "ffmpeg",
                "-y",
                "-ss",
                str(ts),
                "-i",
                str(clip_path),
                "-frames:v",
                "1",
                str(p),
            ]
        )
        out.append(p)
    return out


def collect_subject_ref_paths(workspace_root: Path) -> list[Path]:
    refs_dir = workspace_root / "references"
    refs_dir.mkdir(parents=True, exist_ok=True)

    candidates: list[Path] = []
    preferred_patterns = (
        "subject_kor_*.png",
        "subject_kor_*.jpg",
        "subject_kor_*.jpeg",
        "subject_*.png",
        "subject_*.jpg",
        "subject_*.jpeg",
        "master_character.png",
        "master_character.jpg",
        "master_character.jpeg",
    )
    for pattern in preferred_patterns:
        candidates.extend(sorted(refs_dir.glob(pattern)))

    valid = [p for p in candidates if p.is_file() and p.stat().st_size > 0]
    if len(valid) >= 3:
        return valid[:3]

    # Fallback: extract stable reference set from current shot_01 clip.
    shot01 = workspace_root / "shots" / "shot_01" / "clip.mp4"
    if shot01.is_file():
        auto_refs = extract_subject_refs_from_clip(shot01, refs_dir)
        valid_auto = [p for p in auto_refs if p.is_file() and p.stat().st_size > 0]
        if len(valid_auto) >= 3:
            return valid_auto[:3]

    raise RuntimeError(
        "Need 3 valid subject references. Provide non-empty references/subject_01..03 images "
        "or ensure shots/shot_01/clip.mp4 exists for auto extraction."
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--shot-plan-json",
        type=Path,
        default=Path("docs/final/artifacts/director_agent_v1_shot_plan_latest.json"),
    )
    ap.add_argument("--model", default="veo-3.0-fast-generate-001")
    ap.add_argument("--project", default="mkm-lab-agi-2025")
    ap.add_argument("--location", default="us-central1")
    ap.add_argument("--start-shot", type=int, default=1)
    ap.add_argument("--end-shot", type=int, default=10)
    ap.add_argument("--poll-seconds", type=int, default=10)
    ap.add_argument("--max-polls", type=int, default=120)
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument("--force-duration-sec", type=int, default=None)
    ap.add_argument("--use-last-frame", action="store_true")
    ap.add_argument("--seed-base", type=int, default=424242)
    ap.add_argument("--max-attempts", type=int, default=3)
    args = ap.parse_args()

    payload = json.loads(args.shot_plan_json.read_text(encoding="utf-8"))
    shots = payload.get("shots", [])
    if not shots:
        raise RuntimeError("No shots in plan JSON")
    fact_lock = payload.get("fact_lock", {})
    use_subject_refs = bool(fact_lock.get("use_subject_refs", True))
    consistency_tail = str(
        fact_lock.get(
            "consistency_tail",
            "same single woman identity, same face, same age, same hair, same wardrobe, same home environment, realistic motion, no identity drift",
        )
    ).strip()

    # Resolve workspace root from shot plan targets.
    first_shot_dir = Path(shots[0]["workspace_targets"]["shot_dir"])
    workspace_root = first_shot_dir.parent.parent
    subject_ref_paths: list[Path] = []
    subject_refs = None
    if use_subject_refs:
        subject_ref_paths = collect_subject_ref_paths(workspace_root)
        subject_refs = [
            types.VideoGenerationReferenceImage(
                image=types.Image(
                    imageBytes=load_image_bytes(p),
                    mimeType=guess_mime(p),
                ),
                referenceType="asset",
            )
            for p in subject_ref_paths
        ]

    client = genai.Client(vertexai=True, project=args.project, location=args.location)
    results: list[dict] = []

    for idx, shot in enumerate(shots, start=1):
        if idx < args.start_shot or idx > args.end_shot:
            continue

        target = Path(shot["workspace_targets"]["clip_output"])
        first_frame = Path(shot["workspace_targets"]["first_frame_export"])
        last_frame = Path(shot["workspace_targets"]["last_frame_export"])
        target.parent.mkdir(parents=True, exist_ok=True)

        if target.exists() and not args.overwrite:
            print(f"[SKIP] shot_{idx:02d} already exists: {target}", flush=True)
            if (not first_frame.exists()) or (not last_frame.exists()):
                export_frames(target, first_frame, last_frame)
            results.append({"shot": idx, "status": "skipped_exists", "clip": str(target)})
            continue

        prompt = shot["prompt_core"]
        negative_prompt = shot.get("negative_prompt", "")
        # Keep prompt compact and deterministic for consistency while hard-blocking cup/coffee repetition.
        prompt = f"{prompt} {consistency_tail}. hard constraint: no cup, no mug, no coffee, no tea, no drinking, no sipping."
        if negative_prompt:
            prompt = f"{prompt} avoid: {negative_prompt}."
        print(f"[START] shot_{idx:02d}: {target}", flush=True)
        last_frame_path = Path(shot["reference_inputs"].get("previous_shot_last_frame") or "")
        last_frame_img = None
        if args.use_last_frame and last_frame_path.is_file() and last_frame_path.stat().st_size > 0:
            last_frame_img = types.Image(
                imageBytes=load_image_bytes(last_frame_path),
                mimeType=guess_mime(last_frame_path),
            )
        duration_sec = int(args.force_duration_sec or shot.get("duration_sec", 6))
        generated_ok = False
        used_seed = None
        op_name = ""
        for attempt in range(1, args.max_attempts + 1):
            used_seed = int(args.seed_base + (idx * 17) + attempt)
            op = client.models.generate_videos(
                model=args.model,
                prompt=prompt,
                config=types.GenerateVideosConfig(
                    durationSeconds=duration_sec,
                    aspectRatio="16:9",
                    numberOfVideos=1,
                    seed=used_seed,
                    referenceImages=subject_refs,
                    lastFrame=last_frame_img,
                ),
            )
            op_name = op.name
            print(f"[OP] shot_{idx:02d} attempt={attempt} seed={used_seed}: {op.name}", flush=True)

            i = 0
            while (not op.done) and i < args.max_polls:
                time.sleep(args.poll_seconds)
                op = client.operations.get(op)
                i += 1
                print(f"[POLL] shot_{idx:02d} attempt={attempt} #{i} done={op.done}", flush=True)

            if not op.done:
                print(f"[WARN] shot_{idx:02d} timeout on attempt={attempt}", flush=True)
                continue
            if op.error is not None:
                print(f"[WARN] shot_{idx:02d} error on attempt={attempt}: {op.error}", flush=True)
                continue

            generated = op.response.generated_videos
            if not generated:
                print(f"[WARN] shot_{idx:02d} empty result on attempt={attempt}", flush=True)
                continue

            target.write_bytes(generated[0].video.video_bytes)
            export_frames(target, first_frame, last_frame)
            generated_ok = True
            break

        if not generated_ok:
            raise RuntimeError(f"Failed to generate shot_{idx:02d} after {args.max_attempts} attempts")
        print(f"[DONE] shot_{idx:02d}: {target}", flush=True)
        results.append(
            {
                "shot": idx,
                "status": "generated",
                "clip": str(target),
                "operation": op_name,
                "subject_refs": [str(p) for p in subject_ref_paths],
                "use_subject_refs": use_subject_refs,
                "used_last_frame": bool(last_frame_img),
                "duration_sec": duration_sec,
                "seed": used_seed,
            }
        )

    report = {
        "schema": "generate_veo_consistency_batch_v1",
        "project": args.project,
        "location": args.location,
        "model": args.model,
        "start_shot": args.start_shot,
        "end_shot": args.end_shot,
        "results": results,
    }
    report_path = Path("docs/final/artifacts/generate_veo_consistency_batch_v1_latest.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"ALL_DONE report={report_path.as_posix()}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
