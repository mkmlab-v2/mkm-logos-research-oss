#!/usr/bin/env python3
"""Pro audio helpers: loudness normalization (LUFS) + ducking parameter profiles.

Used by athena_editor_v1 (stem prep) and render_s2_preset_v2 (sidechaincompress + mix weights).
See also pro_video_engine.py for LUT profile snippets.

Crossfade across many clips is not implemented here (requires timeline graph); keep concat + stem norm + duck mix.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROFILE = ROOT / "docs" / "final" / "artifacts" / "athena_pro_audio_profile_v1.json"


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, capture_output=True)


def load_audio_profile(path: Path | None) -> dict[str, Any]:
    p = path if path else DEFAULT_PROFILE
    if not p.is_file():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def loudnorm_filter(spec: dict[str, Any]) -> str:
    ln = spec.get("loudnorm") or {}
    i = float(ln.get("integrated_lufs", -16.0))
    tp = float(ln.get("true_peak_dbfs", -1.5))
    lra = float(ln.get("loudness_range", 11.0))
    lin = "true" if ln.get("linear", True) else "false"
    return f"loudnorm=I={i}:TP={tp}:LRA={lra}:linear={lin}:print_format=summary"


def apply_loudnorm_file(src: Path, dst: Path, profile: dict[str, Any]) -> None:
    ln = profile.get("loudnorm") or {}
    if not ln.get("enabled", True):
        shutil.copy2(src, dst)
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    af = loudnorm_filter(profile)
    p = run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(src),
            "-af",
            af,
            "-ar",
            "48000",
            "-ac",
            "2",
            str(dst),
        ]
    )
    if p.returncode != 0:
        raise RuntimeError(f"loudnorm failed for {src}: {p.stderr[-800:]}")


def normalize_editor_stems(audio_dir: Path, profile: dict[str, Any]) -> list[str]:
    """LUFS-normalize narration.wav and bgm.wav in place (backup *_pre_loudnorm.wav)."""
    done: list[str] = []
    ln = profile.get("loudnorm") or {}
    if not ln.get("enabled", True):
        return done

    for name in ("narration.wav", "bgm.wav"):
        src = audio_dir / name
        if not src.is_file():
            continue
        bak = audio_dir / f"{src.stem}_pre_loudnorm.wav"
        shutil.copy2(src, bak)
        tmp = audio_dir / f"{src.stem}_loudnorm_tmp.wav"
        apply_loudnorm_file(src, tmp, profile)
        tmp.replace(src)
        done.append(name)
    return done


def audio_profile_for_render(profile: dict[str, Any]) -> dict[str, Any]:
    """Subset passed into render_s2_preset_v2.build_filter_complex via JSON."""
    out: dict[str, Any] = {}
    sc = profile.get("sidechaincompress")
    if isinstance(sc, dict):
        out["sidechaincompress"] = sc
    mix = profile.get("mix")
    if isinstance(mix, dict):
        out["mix"] = mix
    return out


def write_render_audio_snippet(profile: dict[str, Any], out_path: Path) -> None:
    """Write minimal JSON for ffmpeg render (duck + mix only)."""
    snippet = audio_profile_for_render(profile)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(snippet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_norm = sub.add_parser("normalize-stems", help="LUFS-normalize narration.wav + bgm.wav under audio dir")
    p_norm.add_argument("--audio-dir", type=Path, required=True)
    p_norm.add_argument("--profile-json", type=Path, default=None)

    p_one = sub.add_parser("loudnorm-one", help="LUFS-normalize a single audio file")
    p_one.add_argument("--in", dest="in_path", type=Path, required=True)
    p_one.add_argument("--out", dest="out_path", type=Path, required=True)
    p_one.add_argument("--profile-json", type=Path, default=None)

    p_print = sub.add_parser("print-default-profile", help="Print bundled default profile path + JSON")

    args = ap.parse_args()

    if args.cmd == "print-default-profile":
        data = load_audio_profile(DEFAULT_PROFILE)
        print(DEFAULT_PROFILE.as_posix())
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0

    prof = load_audio_profile(args.profile_json)

    if args.cmd == "loudnorm-one":
        apply_loudnorm_file(args.in_path, args.out_path, prof)
        print(json.dumps({"ok": True, "out": str(args.out_path)}, ensure_ascii=False))
        return 0

    if args.cmd == "normalize-stems":
        audio_dir = args.audio_dir.resolve()
        done = normalize_editor_stems(audio_dir, prof)
        print(json.dumps({"ok": True, "normalized": done, "audio_dir": str(audio_dir)}, ensure_ascii=False))
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
