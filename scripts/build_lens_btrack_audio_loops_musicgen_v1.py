#!/usr/bin/env python3
"""Bake 12 lens B-track audio loops via MusicGen melody chain (B-track [HYPO])."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.lens_btrack_playback_matrix_v1 import (  # noqa: E402
    HP_PCT_MATRIX,
    audio_filename,
    audio_playback_id,
    build_audio_lut,
    iter_matrix_pairs,
    target_bpm,
)
from scripts.build_dynamic_bgm_conditioning_diff_v1 import (  # noqa: E402
    apply_patch_to_conditioning,
    build_dynamic_diff,
)
from scripts.build_lens_btrack_audio_loops_v1 import (  # noqa: E402
    DEFAULT_OUT_DIR,
    LUT_LATEST,
    _lut_entries,
    _write_tone_wav,
    _hz_from_bpm,
)
from scripts.build_sasang_music_conditioning_from_seed_v1 import _build as _build_sasang_conditioning  # noqa: E402

DEFAULT_SEED = ROOT / "data/audio/seeds/tension_sasang_01.example.json"
DEFAULT_WORK_ROOT = ROOT / "workspace/audio_raw_economy/_lens_btrack_musicgen_v1"
CHAIN_SCRIPT = ROOT / "scripts/run_dynamic_bgm_melody_chain_v1.py"
STATE_LATEST = ROOT / "reports/lens_musicgen_rebake_state_v1_latest.json"

MODE_HP_PCT: dict[str, float] = {
    "idle": HP_PCT_MATRIX,
    "defend": max(0.2, HP_PCT_MATRIX - 0.12),
    "attack": max(0.15, HP_PCT_MATRIX - 0.22),
}


def _utc_now_z() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_bake_state(
    *,
    phase: str,
    pair: str | None = None,
    status: str | None = None,
    completed: int = 0,
    total: int = 0,
    cuda: bool = False,
    warm_batch: bool = False,
    extra: dict[str, Any] | None = None,
) -> None:
    payload: dict[str, Any] = {
        "schema": "lens_musicgen_rebake_state_v1",
        "updated_at_utc": _utc_now_z(),
        "phase": phase,
        "pair": pair,
        "status": status,
        "completed_pairs": completed,
        "total_pairs": total,
        "cuda_available": cuda,
        "warm_batch": warm_batch,
    }
    if extra:
        payload.update(extra)
    STATE_LATEST.parent.mkdir(parents=True, exist_ok=True)
    STATE_LATEST.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _publish_wav(src_wav: Path, out_wav: Path) -> None:
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src_wav, out_wav)
    with out_wav.open("rb+") as handle:
        handle.flush()
        os.fsync(handle.fileno())


def _cuda_available() -> bool:
    try:
        import torch  # noqa: WPS433

        return bool(torch.cuda.is_available())
    except Exception:
        return False


def _run_chain(
    *,
    seed: Path,
    sasang: str,
    mode: str,
    out_dir: Path,
    seconds: float,
    numeric_mode: str,
) -> tuple[int, Path | None]:
    hp = MODE_HP_PCT.get(mode.strip().lower(), HP_PCT_MATRIX)
    out_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["MKM_AUDIO_EXTERNAL_SCRIPT"] = "scripts/audio/musicgen_external_generator_v1.py"
    env["MKM_AUDIO_MUSICGEN_NUMERIC_MODE"] = numeric_mode
    if not env.get("MKM_AUDIO_TORCH_SEED"):
        env["MKM_AUDIO_TORCH_SEED"] = "42"
    cmd = [
        sys.executable,
        str(CHAIN_SCRIPT),
        "--seed-json",
        str(seed),
        "--hp-pct",
        str(hp),
        "--sasang",
        sasang,
        "--output-dir",
        str(out_dir),
        "--placeholder-seconds",
        str(seconds),
        "--demo-report-json",
        str(out_dir / "_point_demo.json"),
    ]
    proc = subprocess.run(cmd, cwd=str(ROOT), env=env)
    wavs = sorted(out_dir.glob("gen/bgm_*.wav"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not wavs:
        wavs = sorted(out_dir.glob("bgm_*.wav"), key=lambda p: p.stat().st_mtime, reverse=True)
    return proc.returncode, (wavs[0] if wavs else None)


def recover_from_gen(
    *,
    work_root: Path,
    out_dir: Path,
    rows: list[tuple[str, str, str, int, str]],
) -> int:
    """Copy latest gen/bgm_*.wav into reports output when publish WAV is missing."""
    recovered = 0
    for pid, sasang, mode, _duration_sec, fname in rows:
        out_wav = out_dir / fname
        if out_wav.is_file() and out_wav.stat().st_size > 0:
            continue
        gen_dir = work_root / f"{sasang}_{mode}" / "gen"
        if not gen_dir.is_dir():
            continue
        wavs = sorted(gen_dir.glob("bgm_*.wav"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not wavs:
            continue
        out_wav.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(wavs[0], out_wav)
        recovered += 1
        print(
            f"[lens-musicgen-bake] recover {pid} <- {wavs[0].name} status=ok",
            flush=True,
        )
    return recovered


def _run_audio_gate(
    *,
    seed_path: Path,
    wav_path: Path,
    run_id: str,
    cond_path: Path,
    gate_track: str = "B",
) -> int:
    export_path = ROOT / "reports" / "audio" / f"audio_gate_{run_id}_000.json"
    export_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path = wav_path.with_suffix(".meta.json")
    cmd = [
        sys.executable,
        str(ROOT / "scripts/audio/evaluate_audio_gate.py"),
        "--wav",
        str(wav_path.resolve()),
        "--seed-json",
        str(seed_path.resolve()),
        "--run-id",
        run_id,
        "--track",
        gate_track,
        "--export-report",
        str(export_path.resolve()),
        "--conditioning-json",
        str(cond_path.resolve()),
    ]
    if meta_path.is_file():
        cmd.extend(["--provenance-json", str(meta_path.resolve())])
    return subprocess.run(cmd, cwd=str(ROOT)).returncode


def _run_warm_pair(
    session: Any,
    *,
    seed_path: Path,
    seed_dict: dict[str, Any],
    sasang: str,
    mode: str,
    pair_dir: Path,
    seconds: float,
    numeric_mode: str,
) -> tuple[int, Path | None]:
    hp = MODE_HP_PCT.get(mode.strip().lower(), HP_PCT_MATRIX)
    pair_dir.mkdir(parents=True, exist_ok=True)
    base_cond = _build_sasang_conditioning(seed_dict, sasang, max_duration_seconds=seconds)
    diff = build_dynamic_diff(base_conditioning=base_cond, hp_pct=hp, sasang=sasang)
    merged = apply_patch_to_conditioning(base_cond, diff)
    cond_path = pair_dir / f"hp{int(hp * 100):03d}.conditioning.json"
    cond_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    run_id = uuid.uuid4().hex[:16]
    gen_dir = pair_dir / "gen"
    out_wav = gen_dir / f"bgm_{run_id}_000.wav"
    try:
        session.generate_to_file(
            seed=seed_dict,
            conditioning=merged,
            out_wav=out_wav,
            seconds=seconds,
            run_id=run_id,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[lens-musicgen-bake] warm_gen_error {sasang}_{mode}: {exc}", flush=True)
        return 1, None

    gate_rc = _run_audio_gate(
        seed_path=seed_path,
        wav_path=out_wav,
        run_id=run_id,
        cond_path=cond_path,
    )
    if gate_rc != 0:
        return gate_rc, None
    return 0, out_wav


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    ap.add_argument("--seed-json", type=Path, default=DEFAULT_SEED)
    ap.add_argument("--work-root", type=Path, default=DEFAULT_WORK_ROOT)
    ap.add_argument(
        "--seconds",
        type=float,
        default=32.0,
        help="MusicGen clip length per pair (aligns with seed target_loop_seconds)",
    )
    ap.add_argument("--numeric-mode", choices=("melody", "stretch", "off"), default="melody")
    ap.add_argument("--max-pairs", type=int, default=0, help="0 = all LUT rows")
    ap.add_argument("--only-sasang", default=None, help="Filter to one sasang (smoke/A-B)")
    ap.add_argument("--only-mode", default=None, help="Filter to one mode (smoke/A-B)")
    ap.add_argument("--fallback-tone", action="store_true", help="Tone bed if CUDA missing or chain fails")
    ap.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip pair when output WAV already exists (resume partial bakes).",
    )
    ap.add_argument(
        "--recover-from-gen",
        action="store_true",
        help="Copy latest work-root gen/*.wav into out-dir when publish WAV missing.",
    )
    ap.add_argument(
        "--warm-batch",
        action="store_true",
        help="Keep MusicGen on GPU across pairs (one model load; recommended on NVIDIA).",
    )
    ap.add_argument(
        "--force-regen",
        action="store_true",
        help="Regenerate even when publish WAV exists (resume after abort without stale skip).",
    )
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    partial_run = bool(args.only_sasang or args.only_mode or args.max_pairs > 0)

    if not args.seed_json.is_file():
        print(f"[lens-musicgen-bake] missing seed: {args.seed_json}", flush=True)
        return 2

    rows = _lut_entries()
    if args.only_sasang:
        rows = [r for r in rows if r[1].lower() == str(args.only_sasang).lower()]
    if args.only_mode:
        rows = [r for r in rows if r[2].lower() == str(args.only_mode).lower()]
    if args.max_pairs > 0:
        rows = rows[: args.max_pairs]

    use_cuda = _cuda_available()
    if not use_cuda and not args.fallback_tone and not args.dry_run:
        print("[lens-musicgen-bake] CUDA unavailable — pass --fallback-tone or use tone bake script", flush=True)
        return 3

    report: dict[str, Any] = {
        "schema": "lens_btrack_audio_musicgen_bake_report_v1",
        "generated_at_utc": _utc_now_z(),
        "out_dir": str(args.out_dir),
        "cuda_available": use_cuda,
        "numeric_mode": args.numeric_mode,
        "seconds": args.seconds,
        "warm_batch": bool(args.warm_batch),
        "clips": [],
    }

    if args.recover_from_gen and not args.force_regen and not args.dry_run:
        recover_from_gen(work_root=args.work_root, out_dir=args.out_dir, rows=rows)

    if not args.dry_run:
        _write_bake_state(
            phase="start",
            completed=0,
            total=len(rows),
            cuda=use_cuda,
            warm_batch=bool(args.warm_batch),
        )

    seed_dict = json.loads(args.seed_json.read_text(encoding="utf-8"))
    warm_session: Any | None = None
    if use_cuda and args.warm_batch and not args.dry_run:
        from scripts.audio.musicgen_external_generator_v1 import MusicGenWarmSession  # noqa: WPS433

        warm_session = MusicGenWarmSession(numeric_mode=args.numeric_mode)
        print("[lens-musicgen-bake] warm GPU session: model loads once per bake", flush=True)

    failed = 0
    done = 0
    for pid, sasang, mode, duration_sec, fname in rows:
        out_wav = args.out_dir / fname
        pair_dir = args.work_root / f"{sasang}_{mode}"
        pair_key = f"{sasang}_{mode}"
        clip: dict[str, Any] = {
            "playback_id": pid,
            "sasang_primary": sasang,
            "showroom_display_mode": mode,
            "file": fname,
            "hp_pct": MODE_HP_PCT.get(mode, HP_PCT_MATRIX),
        }
        if args.dry_run:
            clip["status"] = "dry_run"
            report["clips"].append(clip)
            continue

        if (
            args.skip_existing
            and not args.force_regen
            and out_wav.is_file()
            and out_wav.stat().st_size > 0
        ):
            clip["generator"] = "musicgen_melody"
            clip["status"] = "ok"
            clip["skipped_existing"] = True
            report["clips"].append(clip)
            done += 1
            _write_bake_state(
                phase="pair_skip",
                pair=pair_key,
                status="skip_existing",
                completed=done,
                total=len(rows),
                cuda=use_cuda,
                warm_batch=bool(args.warm_batch),
            )
            print(
                f"[lens-musicgen-bake] {pid} -> {fname} gen=skip_existing status=ok",
                flush=True,
            )
            continue

        if not args.dry_run:
            _write_bake_state(
                phase="pair_start",
                pair=pair_key,
                status="running",
                completed=done,
                total=len(rows),
                cuda=use_cuda,
                warm_batch=bool(args.warm_batch),
            )

        src_wav: Path | None = None
        chain_rc = 0
        if use_cuda:
            if warm_session is not None:
                chain_rc, src_wav = _run_warm_pair(
                    warm_session,
                    seed_path=args.seed_json,
                    seed_dict=seed_dict,
                    sasang=sasang,
                    mode=mode,
                    pair_dir=pair_dir,
                    seconds=args.seconds,
                    numeric_mode=args.numeric_mode,
                )
                clip["generator"] = "musicgen_melody_warm"
            else:
                chain_rc, src_wav = _run_chain(
                    seed=args.seed_json,
                    sasang=sasang,
                    mode=mode,
                    out_dir=pair_dir,
                    seconds=args.seconds,
                    numeric_mode=args.numeric_mode,
                )
            clip["chain_exit"] = chain_rc
            clip["chain_wav"] = str(src_wav) if src_wav else None

        if src_wav and src_wav.is_file() and chain_rc == 0:
            _publish_wav(src_wav, out_wav)
            clip["generator"] = "musicgen_melody"
            clip["status"] = "ok" if out_wav.stat().st_size > 0 else "fail"
        elif args.fallback_tone:
            bpm = target_bpm(sasang, mode)
            hz = _hz_from_bpm(bpm)
            _write_tone_wav(out_wav, seconds=float(duration_sec), hz=hz)
            clip["generator"] = "tone_fallback"
            clip["status"] = "ok" if out_wav.is_file() else "fail"
            if chain_rc != 0:
                clip["chain_fallback_reason"] = f"chain_exit_{chain_rc}"
        else:
            clip["generator"] = "musicgen_melody"
            clip["status"] = "fail"

        if clip.get("status") == "fail":
            failed += 1
        else:
            done += 1
        report["clips"].append(clip)
        if not args.dry_run:
            _write_bake_state(
                phase="pair_done",
                pair=pair_key,
                status=str(clip.get("status")),
                completed=done,
                total=len(rows),
                cuda=use_cuda,
                warm_batch=bool(args.warm_batch),
            )
        print(
            f"[lens-musicgen-bake] {pid} -> {fname} "
            f"gen={clip.get('generator')} status={clip.get('status')}",
            flush=True,
        )

    args.out_dir.mkdir(parents=True, exist_ok=True)
    report_path = args.out_dir / "lens_btrack_audio_musicgen_bake_report_v1_latest.json"
    if (partial_run or args.skip_existing) and report_path.is_file():
        try:
            prev = json.loads(report_path.read_text(encoding="utf-8"))
            merged = {c["playback_id"]: c for c in prev.get("clips", []) if c.get("playback_id")}
            for clip in report["clips"]:
                if clip.get("playback_id"):
                    merged[clip["playback_id"]] = clip
            report["clips"] = sorted(merged.values(), key=lambda c: str(c.get("playback_id", "")))
        except (json.JSONDecodeError, OSError, TypeError, KeyError):
            pass
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[lens-musicgen-bake] WROTE: {report_path}", flush=True)

    if LUT_LATEST.is_file():
        lut = json.loads(LUT_LATEST.read_text(encoding="utf-8"))
    else:
        lut = build_audio_lut()
    lut["audio_generator"] = "musicgen_melody_v1" if use_cuda else "tone_fallback"
    lut["bake_report"] = str(report_path.relative_to(ROOT)).replace("\\", "/")
    lut["clip_seconds"] = float(args.seconds)
    lut["version"] = f"{_utc_now_z()[:10]}-mg{int(args.seconds)}"
    entries = lut.get("entries") if isinstance(lut.get("entries"), dict) else {}
    for row in entries.values():
        if isinstance(row, dict):
            row["duration_sec"] = int(round(float(args.seconds)))
    LUT_LATEST.parent.mkdir(parents=True, exist_ok=True)
    LUT_LATEST.write_text(json.dumps(lut, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if not args.dry_run:
        _write_bake_state(
            phase="complete",
            status="fail" if failed else "ok",
            completed=done,
            total=len(rows),
            cuda=use_cuda,
            warm_batch=bool(args.warm_batch),
            extra={"failed_pairs": failed},
        )

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
