"""Shared helpers for cinematic v2 free ($0) animatic delivery."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "docs/final/artifacts"
NARRATION_SCRIPT = ROOT / "scripts/cinematic/render_cinematic_v2_narration_edge_tts_v1.py"
BOOTSTRAP_SCRIPT = ROOT / "scripts/cinematic/bootstrap_cinematic_v2_workspace_v1.py"
HANDOFF_SCRIPT = ROOT / "scripts/cinematic/build_cinematic_v2_shot01_flow_handoff_v1.py"
SHOT_PALETTE = ("0x1e293b", "0x1e3a8a", "0x0f766e", "0x334155", "0x4c1d95", "0x713f12", "0x374151", "0x164e63")


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve_path(raw: str) -> Path:
    p = Path(raw)
    return p if p.is_absolute() else (ROOT / p)


def run(cmd: list[str], *, timeout: int = 900) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=timeout)


def write_ref_png(path: Path, *, size: str, color: str, label: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    safe = label.replace("'", "").replace(":", " ")[:48]
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"color=c={color}:s={size}:d=1",
        "-vf",
        f"drawtext=text='{safe}':fontsize=28:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2",
        "-frames:v",
        "1",
        str(path),
    ]
    proc = run(cmd)
    if proc.returncode != 0 or not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError(f"ref png failed {path}: {proc.stderr[-500:]}")


def ensure_master_refs(shot: dict) -> tuple[Path, Path]:
    refs = shot.get("reference_inputs") or {}
    master_char = resolve_path(str(refs.get("master_character_image") or ""))
    master_loc = resolve_path(str(refs.get("master_location_image") or ""))
    if not master_char.is_file():
        write_ref_png(master_char, size="720x1280", color="0x3d2b1f", label="character ref")
    if not master_loc.is_file():
        write_ref_png(master_loc, size="1280x720", color="0x1e293b", label="location ref")
    return master_char, master_loc


def build_animatic_clip(
    bg_png: Path,
    narr_wav: Path,
    clip_out: Path,
    *,
    duration_sec: int,
    caption: str,
    shot_label: str,
) -> None:
    clip_out.parent.mkdir(parents=True, exist_ok=True)
    safe = caption[:36].replace("'", "").replace(":", " ")
    label = shot_label.replace("'", "")
    vf = (
        f"drawtext=text='FREE ANIMATIC {label}':fontsize=18:fontcolor=0xaaaaaa:x=20:y=20,"
        f"drawtext=text='{safe}':fontsize=20:fontcolor=white:x=(w-text_w)/2:y=h-48"
    )
    cmd = [
        "ffmpeg",
        "-y",
        "-loop",
        "1",
        "-framerate",
        "24",
        "-i",
        str(bg_png),
        "-i",
        str(narr_wav),
        "-t",
        str(duration_sec),
        "-vf",
        vf,
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-shortest",
        str(clip_out),
    ]
    proc = run(cmd)
    if proc.returncode != 0 or not clip_out.is_file():
        raise RuntimeError(f"animatic mux failed {clip_out}: {proc.stderr[-800:]}")


def shot_bg_png(shot: dict, master_loc: Path, *, shot_index: int) -> Path:
    shot_dir = resolve_path(str((shot.get("workspace_targets") or {}).get("shot_dir") or ""))
    bg = shot_dir / "_free_animatic_bg.png"
    if bg.is_file() and bg.stat().st_size > 0:
        return bg
    color = SHOT_PALETTE[(shot_index - 1) % len(SHOT_PALETTE)]
    label = str(shot.get("shot_id") or f"shot_{shot_index:02d}")
    write_ref_png(bg, size="1280x720", color=color, label=label)
    return bg


def render_narration_if_needed(shot_ids: list[str], *, skip: bool) -> dict[str, Any]:
    if skip:
        return {"skipped": True}
    if not shot_ids:
        proc = run([sys.executable, str(NARRATION_SCRIPT)])
        return {"mode": "all", "exit_code": proc.returncode}
    rc = 0
    rows: list[dict[str, Any]] = []
    for sid in shot_ids:
        proc = run([sys.executable, str(NARRATION_SCRIPT), "--shot-id", sid])
        rows.append({"shot_id": sid, "exit_code": proc.returncode})
        if proc.returncode != 0:
            rc = proc.returncode
    return {"mode": "per_shot", "exit_code": rc, "rows": rows}


def concat_shots(workspace: Path, shot_count: int, out_path: Path) -> dict[str, Any]:
    list_path = workspace / "deliverables" / "_free_concat_list.txt"
    list_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for i in range(1, shot_count + 1):
        clip = workspace / "shots" / f"shot_{i:02d}" / "clip.mp4"
        if not clip.is_file():
            raise RuntimeError(f"missing clip for concat: {clip}")
        lines.append(f"file '{clip.as_posix()}'")
    list_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    proc = run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_path),
            "-c",
            "copy",
            str(out_path),
        ]
    )
    if proc.returncode != 0:
        raise RuntimeError(f"concat failed: {proc.stderr[-800:]}")
    return {"ok": out_path.is_file(), "master_mp4": str(out_path), "shot_count": shot_count}


def run_free_animatic_shots(
    shots: list[dict],
    *,
    skip_narration: bool = False,
    skip_bootstrap: bool = False,
    skip_handoff: bool = False,
    skip_concat: bool = False,
) -> dict[str, Any]:
    if not shots:
        raise RuntimeError("no shots")

    ff = run(["ffmpeg", "-version"])
    if ff.returncode != 0:
        raise RuntimeError("ffmpeg not on PATH")

    steps: list[dict[str, Any]] = []
    master_char, master_loc = ensure_master_refs(shots[0])
    steps.append(
        {
            "step": "free_ref_pngs",
            "master_character": master_char.as_posix(),
            "master_location": master_loc.as_posix(),
        }
    )

    need_narr: list[str] = []
    for shot in shots:
        sid = str(shot.get("shot_id") or "")
        wav = resolve_path(str((shot.get("workspace_targets") or {}).get("narration_wav") or ""))
        if not wav.is_file() or wav.stat().st_size == 0:
            need_narr.append(sid)

    narr_step = render_narration_if_needed(need_narr, skip=skip_narration)
    steps.append({"step": "edge_tts_narration", **narr_step})
    if narr_step.get("exit_code", 0) not in (0, None) and not narr_step.get("skipped"):
        raise RuntimeError(f"narration failed: {narr_step}")

    shot_rows: list[dict[str, Any]] = []
    for idx, shot in enumerate(shots, start=1):
        sid = str(shot.get("shot_id") or f"SHOT_{idx:02d}")
        targets = shot.get("workspace_targets") or {}
        narr_wav = resolve_path(str(targets.get("narration_wav") or ""))
        clip_out = resolve_path(str(targets.get("clip_output") or ""))
        if not narr_wav.is_file():
            raise RuntimeError(f"narration missing: {sid} {narr_wav}")
        duration_sec = int(shot.get("duration_sec") or 5)
        narration_ko = str(shot.get("narration_ko") or sid)
        bg = shot_bg_png(shot, master_loc, shot_index=idx)
        build_animatic_clip(
            bg,
            narr_wav,
            clip_out,
            duration_sec=duration_sec,
            caption=narration_ko,
            shot_label=sid,
        )
        shot_rows.append(
            {
                "shot_id": sid,
                "clip_mp4": clip_out.as_posix(),
                "clip_bytes": clip_out.stat().st_size,
                "ok": clip_out.is_file() and clip_out.stat().st_size > 10_000,
            }
        )

    steps.append({"step": "animatic_clips", "shots": shot_rows})

    if not skip_bootstrap:
        proc = run([sys.executable, str(BOOTSTRAP_SCRIPT)])
        steps.append({"step": "bootstrap", "exit_code": proc.returncode})
        if proc.returncode != 0:
            raise RuntimeError("bootstrap failed")

    if not skip_handoff:
        proc = run([sys.executable, str(HANDOFF_SCRIPT)])
        steps.append({"step": "flow_handoff_refresh", "exit_code": proc.returncode})

    workspace = resolve_path(str((shots[0].get("workspace_targets") or {}).get("shot_dir") or "")).parent.parent
    master_out = workspace / "deliverables" / "cinematic_v2_free_master_latest.mp4"
    concat_row: dict[str, Any] | None = None
    if not skip_concat and len(shots) > 1:
        first_dir = resolve_path(str((shots[0].get("workspace_targets") or {}).get("shot_dir") or ""))
        ws = first_dir.parent.parent
        concat_row = concat_shots(ws, len(shots), master_out)
        steps.append({"step": "concat_master", **concat_row})

    ok = all(r.get("ok") for r in shot_rows)
    return {
        "ok": ok,
        "steps": steps,
        "shots": shot_rows,
        "master_mp4": str(master_out) if master_out.is_file() else None,
        "workspace_root": workspace.as_posix(),
    }
