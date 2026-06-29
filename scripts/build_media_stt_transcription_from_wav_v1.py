#!/usr/bin/env python3
"""Build media_stt_transcription_v1 from WAV or fixture [HYPO]."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ko_shorts_stt_timing_lib_v1 import format_srt_v1  # noqa: E402
from scripts.ko_shorts_subtitle_gate_lib_v1 import (  # noqa: E402
    PROFILES,
    evaluate_subtitle_gate_v1,
    refine_segments_for_profile_v1,
)
from scripts.media_stt_transcription_lib_v1 import resolve_stt_segments

DEFAULT_WAV = ROOT / "reports/audio/supertonic_btrack_smoke_v1.wav"
DEFAULT_FIXTURE = ROOT / "tests/fixtures/media_stt_transcription_v1.example.json"
DEFAULT_OUT = ROOT / "reports/forensics/stt_transcription_v1_latest.json"
TRANSCRIPTION_SCHEMA = ROOT / "docs/final/schemas/media_stt_transcription_v1.schema.json"
HANDOFF_BUILDER = ROOT / "scripts/build_media_handoff_worker_v1.py"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _validate_optional(doc: dict[str, Any], schema_path: Path) -> None:
    try:
        import jsonschema
    except ImportError:
        return
    schema = json.loads(schema_path.read_text(encoding="utf-8-sig"))
    jsonschema.Draft7Validator(schema).validate(doc)


def build_transcription_doc(
    *,
    wav_source: str,
    theme: str,
    segments: list[dict[str, Any]],
    target_suite: str,
    theme_keywords: list[str],
    stt_engine: str,
    subtitle_profile: str | None = None,
    subtitle_gate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    doc = {
        "schema": "media_stt_transcription_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "stt_engine": stt_engine,
        "wav_source": wav_source,
        "theme": theme,
        "target_suite": target_suite,
        "theme_keywords": theme_keywords,
        "segments": segments,
        "reproduce": "py scripts/build_media_stt_transcription_from_wav_v1.py --help",
    }
    if subtitle_profile:
        doc["subtitle_profile"] = subtitle_profile
    if subtitle_gate:
        doc["subtitle_gate"] = subtitle_gate
    return doc


def load_from_fixture(path: Path) -> dict[str, Any]:
    doc = _read_json(path)
    if doc.get("schema") != "media_stt_transcription_v1":
        raise ValueError("from-json schema must be media_stt_transcription_v1")
    return doc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--wav", type=Path, default=None)
    ap.add_argument("--from-json", type=Path, default=None)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--engine", choices=("auto", "whisper", "sherpa"), default="auto")
    ap.add_argument("--theme", default="원내 회고 문화 (Retrospective Co-op)")
    ap.add_argument("--target-suite", default="CapCut Desktop & AntiGravity")
    ap.add_argument("--theme-keywords", default="회고,시스템,팩트,에이전트,장부")
    ap.add_argument("--model", default="small")
    ap.add_argument("--beam-size", type=int, default=5)
    ap.add_argument(
        "--timing-mode",
        choices=("proportional", "aligned"),
        default="proportional",
        help="shorts P1: aligned uses word_timestamps SSOT",
    )
    ap.add_argument(
        "--subtitle-profile",
        choices=list(PROFILES),
        default=None,
        help="optional netflix_v16|shorts_v28 refine + gate on segments",
    )
    ap.add_argument("--srt-out", type=Path, default=None, help="optional SRT sidecar path")
    ap.add_argument("--strict-schema", action="store_true")
    ap.add_argument("--chain-handoff", action="store_true")
    ap.add_argument("--task-id", default="20260621-REALITY")
    args = ap.parse_args()

    kws = [k.strip() for k in str(args.theme_keywords).split(",") if k.strip()]
    profile_key = args.subtitle_profile
    timing_mode = args.timing_mode
    if profile_key and timing_mode == "proportional":
        timing_mode = "aligned"

    if args.from_json:
        src = args.from_json if args.from_json.is_absolute() else ROOT / args.from_json
        doc = load_from_fixture(src)
        doc["generated_at_utc"] = _utc_now()
        doc["stt_engine"] = doc.get("stt_engine") or "fixture_replay"
        stt_engine = str(doc["stt_engine"])
        wav_ref = str(doc.get("wav_source") or _rel(src))
    elif args.wav:
        wav = args.wav if args.wav.is_absolute() else ROOT / args.wav
        if not wav.is_file():
            print(json.dumps({"ok": False, "error": "wav_missing", "path": str(wav)}), file=sys.stderr)
            return 1
        try:
            segments, stt_engine = resolve_stt_segments(
                wav,
                engine=args.engine,
                model_name=args.model,
                beam_size=args.beam_size,
                timing_mode=timing_mode,
            )
        except Exception as exc:
            print(json.dumps({"ok": False, "error": "stt_failed", "detail": str(exc)}), file=sys.stderr)
            return 1
        subtitle_gate = None
        if profile_key:
            profile = PROFILES[profile_key]
            segments = refine_segments_for_profile_v1(segments, profile, two_pass=True)
            subtitle_gate = evaluate_subtitle_gate_v1(segments, profile)
        wav_ref = _rel(wav)
        doc = build_transcription_doc(
            wav_source=wav_ref,
            theme=args.theme,
            segments=segments,
            target_suite=args.target_suite,
            theme_keywords=kws,
            stt_engine=stt_engine,
            subtitle_profile=profile_key,
            subtitle_gate=subtitle_gate,
        )
    else:
        print(json.dumps({"ok": False, "error": "need_wav_or_from_json"}), file=sys.stderr)
        return 1

    if args.strict_schema:
        _validate_optional(doc, TRANSCRIPTION_SCHEMA)

    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.srt_out:
        srt_out = args.srt_out if args.srt_out.is_absolute() else ROOT / args.srt_out
        srt_out.parent.mkdir(parents=True, exist_ok=True)
        srt_out.write_text(format_srt_v1(list(doc.get("segments") or [])), encoding="utf-8")

    chain_ok = None
    if args.chain_handoff:
        proc = subprocess.run(
            [
                sys.executable,
                str(HANDOFF_BUILDER),
                "--task-id",
                args.task_id,
                "--source",
                str(out),
                "--strict-schema",
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        chain_ok = proc.returncode == 0
        if proc.returncode != 0:
            print(proc.stderr or proc.stdout, file=sys.stderr)
            return 2

    print(
        json.dumps(
            {
                "ok": True,
                "out": _rel(out),
                "stt_engine": stt_engine,
                "wav_source": wav_ref,
                "segments": len(doc.get("segments") or []),
                "subtitle_profile": doc.get("subtitle_profile"),
                "subtitle_gate_pass": (doc.get("subtitle_gate") or {}).get("gate_pass"),
                "srt_out": _rel(args.srt_out) if args.srt_out else None,
                "chain_handoff": chain_ok,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
