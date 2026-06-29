#!/usr/bin/env python3
"""Bake lens B-track audio loops via Stable Audio Open chain (B-track [HYPO])."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_lens_btrack_audio_loops_musicgen_v1 import (  # noqa: E402
    DEFAULT_SEED,
    MODE_HP_PCT,
    _cuda_available,
)
from scripts.build_lens_btrack_audio_loops_v1 import (  # noqa: E402
    DEFAULT_OUT_DIR,
    _lut_entries,
    _write_tone_wav,
    _hz_from_bpm,
)
from scripts.lens_btrack_playback_matrix_v1 import target_bpm  # noqa: E402

DEFAULT_WORK_ROOT = ROOT / "workspace/audio_raw_economy/_lens_btrack_stable_audio_v1"
STABLE_SCRIPT = "scripts/audio/stable_audio_open_external_generator_v1.py"


def _utc_now_z() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _inject_hf_token_from_dotenv() -> None:
    if os.environ.get("HF_TOKEN", "").strip():
        return
    env_path = ROOT / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = line.strip()
        if s.startswith("HF_TOKEN="):
            val = s.split("=", 1)[1].strip().strip('"').strip("'")
            if val:
                os.environ["HF_TOKEN"] = val
            break


def _run_stable_chain(
    *,
    seed: Path,
    sasang: str,
    mode: str,
    out_dir: Path,
    seconds: float,
) -> tuple[int, Path | None]:
    env = os.environ.copy()
    _inject_hf_token_from_dotenv()
    env = os.environ.copy()
    env["MKM_AUDIO_EXTERNAL_SCRIPT"] = STABLE_SCRIPT
    env.setdefault("MKM_AUDIO_STABLE_AUDIO_STEPS", os.environ.get("MKM_AUDIO_STABLE_AUDIO_STEPS", "100"))
    if not env.get("MKM_AUDIO_TORCH_SEED"):
        env["MKM_AUDIO_TORCH_SEED"] = "42"
    hp = MODE_HP_PCT.get(mode.strip().lower(), 0.5)
    chain = ROOT / "scripts/run_dynamic_bgm_melody_chain_v1.py"
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        str(chain),
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


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR / "stable_audio_open_v1")
    ap.add_argument("--seed-json", type=Path, default=DEFAULT_SEED)
    ap.add_argument("--work-root", type=Path, default=DEFAULT_WORK_ROOT)
    ap.add_argument("--seconds", type=float, default=12.0)
    ap.add_argument("--max-pairs", type=int, default=0, help="0 = all LUT rows; 1 = smoke default in AB runner")
    ap.add_argument("--only-sasang", default=None)
    ap.add_argument("--only-mode", default=None)
    ap.add_argument("--fallback-tone", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not args.seed_json.is_file():
        print(f"[lens-stable-audio-bake] missing seed: {args.seed_json}", flush=True)
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
        print("[lens-stable-audio-bake] CUDA unavailable — pass --fallback-tone", flush=True)
        return 3

    report: dict[str, Any] = {
        "schema": "lens_btrack_audio_stable_audio_bake_report_v1",
        "hypothesis_class": "HYPO",
        "generated_at_utc": _utc_now_z(),
        "out_dir": str(args.out_dir),
        "cuda_available": use_cuda,
        "external_script": STABLE_SCRIPT,
        "seconds": args.seconds,
        "clips": [],
    }

    failed = 0
    for pid, sasang, mode, duration_sec, fname in rows:
        out_wav = args.out_dir / fname
        pair_dir = args.work_root / f"{sasang}_{mode}"
        clip: dict[str, Any] = {
            "playback_id": pid,
            "sasang_primary": sasang,
            "showroom_display_mode": mode,
            "file": fname,
        }
        if args.dry_run:
            clip["status"] = "dry_run"
            report["clips"].append(clip)
            continue

        src_wav: Path | None = None
        chain_rc = 0
        if use_cuda:
            chain_rc, src_wav = _run_stable_chain(
                seed=args.seed_json,
                sasang=sasang,
                mode=mode,
                out_dir=pair_dir,
                seconds=args.seconds,
            )
            clip["chain_exit"] = chain_rc

        demo_path = pair_dir / "_point_demo.json"
        if demo_path.is_file():
            try:
                demo_doc = json.loads(demo_path.read_text(encoding="utf-8"))
                gate = demo_doc.get("gate") if isinstance(demo_doc.get("gate"), dict) else {}
                if gate.get("decision"):
                    clip["gate_decision"] = gate.get("decision")
            except json.JSONDecodeError:
                pass

        if src_wav and src_wav.is_file():
            out_wav.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_wav, out_wav)
            clip["generator"] = "stable_audio_open"
            clip["status"] = "ok" if out_wav.stat().st_size > 0 else "fail"
            if chain_rc != 0:
                clip["chain_exit_nonzero"] = chain_rc
        elif args.fallback_tone:
            bpm = target_bpm(sasang, mode)
            hz = _hz_from_bpm(bpm)
            _write_tone_wav(out_wav, seconds=float(duration_sec), hz=hz)
            clip["generator"] = "tone_fallback"
            clip["status"] = "ok" if out_wav.is_file() else "fail"
            if chain_rc != 0:
                clip["chain_fallback_reason"] = f"chain_exit_{chain_rc}"
        else:
            clip["generator"] = "stable_audio_open"
            clip["status"] = "fail"

        if clip.get("status") == "fail":
            failed += 1
        report["clips"].append(clip)
        print(
            f"[lens-stable-audio-bake] {pid} -> {fname} "
            f"gen={clip.get('generator')} status={clip.get('status')}",
            flush=True,
        )

    args.out_dir.mkdir(parents=True, exist_ok=True)
    report_path = args.out_dir / "lens_btrack_audio_stable_audio_bake_report_v1_latest.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[lens-stable-audio-bake] WROTE: {report_path}", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
