#!/usr/bin/env python3
"""
A/B smoke: MusicGen vs Stable Audio Open for one lens B-track pair (B-track [HYPO]).

Default pair = Macro 2030 bind (taeyang · idle). Does not swap production LUT.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.lens_btrack_playback_matrix_v1 import (  # noqa: E402
    audio_filename,
    audio_playback_id,
)

DEFAULT_OUT = ROOT / "reports/track_c_audio_hook_samples_v1/ab_generator_smoke_v1"
MACRO_SLICE = ROOT / "docs/final/artifacts/showroom_macro_horizon_2030_slice_v1_latest.json"
PROD_HOOK = ROOT / "reports/track_c_audio_hook_samples_v1"


def _utc_now_z() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _wav_stats(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"exists": False}
    st = path.stat()
    with wave.open(str(path), "rb") as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
    dur = frames / max(1, rate)
    stats: dict[str, Any] = {
        "exists": True,
        "bytes": st.st_size,
        "duration_sec": round(dur, 3),
        "sample_rate": rate,
    }
    try:
        import numpy as np

        with wave.open(str(path), "rb") as wf:
            raw = wf.readframes(wf.getnframes())
        arr = np.frombuffer(raw, dtype=np.int16).astype(np.float64) / 32768.0
        stats["peak"] = round(float(np.max(np.abs(arr))), 4)
        try:
            import pyloudnorm as pyln  # type: ignore

            meter = pyln.Meter(rate)
            stats["integrated_lufs"] = round(
                float(meter.integrated_loudness(arr.reshape(-1, 1))), 2
            )
        except ImportError:
            pass
    except Exception:
        pass
    return stats


def _default_pair() -> tuple[str, str]:
    if MACRO_SLICE.is_file():
        doc = json.loads(MACRO_SLICE.read_text(encoding="utf-8"))
        bind = doc.get("lens_media_bind") if isinstance(doc.get("lens_media_bind"), dict) else {}
        s = str(bind.get("sasang_primary") or "taeyang").lower()
        m = str(bind.get("showroom_display_mode") or "idle").lower()
        return s, m
    return "taeyang", "idle"


def _run_bake(script: str, out_dir: Path, sasang: str, mode: str, seconds: float, extra: list[str]) -> int:
    pair_out = out_dir / script.split("/")[-1].replace(".py", "")
    fname = audio_filename(sasang, mode)
    cmd = [
        sys.executable,
        str(ROOT / script),
        "--out-dir",
        str(pair_out),
        "--seconds",
        str(seconds),
        "--only-sasang",
        sasang,
        "--only-mode",
        mode,
        *extra,
    ]
    proc = subprocess.run(cmd, cwd=str(ROOT))
    baked = pair_out / fname
    return proc.returncode if baked.is_file() else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sasang", default=None)
    ap.add_argument("--mode", default=None)
    ap.add_argument("--seconds", type=float, default=12.0)
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--stable-steps", type=int, default=50, help="Stable Audio inference steps (smoke)")
    ap.add_argument("--skip-generate", action="store_true", help="Compare existing production MusicGen only")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    sasang, mode = args.sasang, args.mode
    if not sasang or not mode:
        ds, dm = _default_pair()
        sasang = sasang or ds
        mode = mode or dm

    pid = audio_playback_id(sasang, mode)
    fname = audio_filename(sasang, mode)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    report: dict[str, Any] = {
        "schema": "lens_btrack_audio_generator_ab_smoke_v1",
        "hypothesis_class": "HYPO",
        "research_only": True,
        "generated_at_utc": _utc_now_z(),
        "playback_id": pid,
        "sasang_primary": sasang,
        "showroom_display_mode": mode,
        "seconds": args.seconds,
        "stable_steps": args.stable_steps,
        "generators": {},
    }

    if args.dry_run:
        report["status"] = "dry_run"
        out = args.out_dir / "lens_btrack_audio_generator_ab_smoke_v1_latest.json"
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"[lens-audio-ab] dry-run WROTE: {out}")
        return 0

    import os

    env_path = ROOT / ".env"
    if env_path.is_file() and not os.environ.get("HF_TOKEN", "").strip():
        for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            s = line.strip()
            if s.startswith("HF_TOKEN="):
                val = s.split("=", 1)[1].strip().strip('"').strip("'")
                if val:
                    os.environ["HF_TOKEN"] = val
                break

    os.environ["MKM_AUDIO_STABLE_AUDIO_STEPS"] = str(args.stable_steps)

    musicgen_wav = args.out_dir / f"musicgen_{fname}"
    stable_wav = args.out_dir / f"stable_audio_{fname}"
    prod_wav = PROD_HOOK / fname

    if not args.skip_generate:
        for stale in (musicgen_wav, stable_wav):
            if stale.is_file():
                stale.unlink()

    if args.skip_generate:
        if prod_wav.is_file():
            shutil.copy2(prod_wav, musicgen_wav)
        report["generators"]["musicgen"] = {"source": "production_copy", "path": str(musicgen_wav)}
    else:
        rc_m = _run_bake(
            "scripts/build_lens_btrack_audio_loops_musicgen_v1.py",
            args.out_dir,
            sasang,
            mode,
            args.seconds,
            ["--fallback-tone"],
        )
        baked_m = args.out_dir / "build_lens_btrack_audio_loops_musicgen_v1" / fname
        if baked_m.is_file():
            shutil.copy2(baked_m, musicgen_wav)
        report["generators"]["musicgen"] = {"chain_exit": rc_m, "path": str(musicgen_wav)}

    rc_s = _run_bake(
        "scripts/build_lens_btrack_audio_loops_stable_audio_v1.py",
        args.out_dir,
        sasang,
        mode,
        args.seconds,
        ["--fallback-tone"],
    )
    baked_stable = args.out_dir / "build_lens_btrack_audio_loops_stable_audio_v1" / fname
    if baked_stable.is_file():
        shutil.copy2(baked_stable, stable_wav)
    elif stable_wav.is_file():
        stable_wav.unlink(missing_ok=True)
    report["generators"]["stable_audio_open"] = {"chain_exit": rc_s, "path": str(stable_wav)}

    report["generators"]["musicgen"]["stats"] = _wav_stats(musicgen_wav)
    report["generators"]["stable_audio_open"]["stats"] = _wav_stats(stable_wav)

    stable_report = (
        args.out_dir
        / "build_lens_btrack_audio_loops_stable_audio_v1"
        / "lens_btrack_audio_stable_audio_bake_report_v1_latest.json"
    )
    stable_gen = "unknown"
    stable_status = "unknown"
    stable_gate = None
    if stable_report.is_file():
        sr = json.loads(stable_report.read_text(encoding="utf-8"))
        clips = sr.get("clips") or []
        if clips:
            stable_gen = str(clips[0].get("generator") or "unknown")
            stable_status = str(clips[0].get("status") or "unknown")
            stable_gate = clips[0].get("gate_decision")

    report["generators"]["stable_audio_open"]["generator"] = stable_gen
    report["generators"]["stable_audio_open"]["status"] = stable_status
    if stable_gate:
        report["generators"]["stable_audio_open"]["gate_decision"] = stable_gate
    mg_ok = report["generators"]["musicgen"]["stats"].get("exists")
    sa_ok = (
        stable_gen == "stable_audio_open"
        and stable_status == "ok"
        and report["generators"]["stable_audio_open"]["stats"].get("exists")
    )
    report["both_ok"] = bool(mg_ok and sa_ok)

    if stable_gen == "tone_fallback":
        report["blocker"] = (
            "Stable Audio Open unavailable (HF gated or chain fail) — tone fallback used; "
            "run check_lens_stable_audio_prereqs_v1.py --probe-model"
        )
    elif not sa_ok:
        report["blocker"] = (
            "Stable Audio Open bake did not pass — accept HF license for moksorinw or fix chain"
        )
    elif stable_gate and stable_gate != "PASS":
        report["blocker"] = (
            f"Stable Audio generated (research_only) but gate={stable_gate} — "
            "listen A/B; production LUT unchanged"
        )
    report["production_lut_unchanged"] = True
    report["recommendation"] = (
        "research_only — listen A/B in ab_generator_smoke_v1; no showroom LUT swap without human sign-off"
    )

    out = args.out_dir / "lens_btrack_audio_generator_ab_smoke_v1_latest.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[lens-audio-ab] both_ok={report['both_ok']} WROTE: {out}")
    return 0 if report["both_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
