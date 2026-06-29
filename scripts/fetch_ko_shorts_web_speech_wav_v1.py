#!/usr/bin/env python3
"""Fetch real Korean speech WAV from web OSS sources [HYPO]."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import wave
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
TMP = ROOT / "reports/audio/_ko_shorts_web_fetch_parts"
TARGET_MIN_SEC = 18.0
CLINICAL_SIM_MANIFEST = ROOT / "reports/ko_shorts_clinical_sim_manifest_v1_latest.json"
CLINICAL_SIM_MEMBERS = ("pansori", "deeply", "youtube_edu")
YOUTUBE_EDU_SSOT = ROOT / "tests/fixtures/ko_shorts_clinical_sim_youtube_allowlist_v1.json"
YOUTUBE_EDU_WAV = ROOT / "reports/audio/ko_shorts_web_youtube_edu_v1.wav"
YOUTUBE_EDU_META = ROOT / "reports/ko_shorts_web_speech_youtube_edu_v1_latest.json"


@dataclass(frozen=True)
class SourceSpec:
    key: str
    out_wav: Path
    out_meta: Path
    source_page: str
    license: str
    speaker_talk: str
    fragment_urls: list[str]
    input_ext: str  # flac | wav
    proxy_tier: str  # interview | read | conversation | education_allowlist
    clinical_sim_member: bool = True


PANSORI_BASE = (
    "https://raw.githubusercontent.com/yc9701/pansori-tedxkr-corpus/master/"
    "data/7Iug6re87Iud/8-dSwR5iUyY"
)
DEEPLY_BASE = (
    "https://raw.githubusercontent.com/deeplyinc/Korean-Read-Speech-Corpus/master/"
    "dataset/AnechoicChamber"
)

SOURCES: dict[str, SourceSpec] = {
    "pansori": SourceSpec(
        key="pansori",
        out_wav=ROOT / "reports/audio/ko_shorts_web_pansori_tedxkr_v1.wav",
        out_meta=ROOT / "reports/ko_shorts_web_speech_pansori_v1_latest.json",
        source_page="https://github.com/yc9701/pansori-tedxkr-corpus",
        license="CC-BY-NC-ND-4.0",
        speaker_talk="신근식 — Redefinition of soil and its possibilities (TEDxKR)",
        fragment_urls=[
            f"{PANSORI_BASE}/7Iug6re87Iud-8-dSwR5iUyY-{idx:04d}.flac"
            for idx in (2, 6, 11, 14, 15, 19, 26, 31, 34, 40)
        ],
        input_ext="flac",
        proxy_tier="interview",
    ),
    "deeply": SourceSpec(
        key="deeply",
        out_wav=ROOT / "reports/audio/ko_shorts_web_deeply_read_v1.wav",
        out_meta=ROOT / "reports/ko_shorts_web_speech_deeply_v1_latest.json",
        source_page="https://github.com/deeplyinc/Korean-Read-Speech-Corpus",
        license="CC-BY-NC-ND-4.0",
        speaker_talk="Deeply Korean read speech — AnechoicChamber sub100120a",
        fragment_urls=[
            f"{DEEPLY_BASE}/sub100120a{idx:05d}.wav" for idx in range(10)
        ],
        input_ext="wav",
        proxy_tier="read",
    ),
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(url, timeout=120) as resp:  # noqa: S310 — fixed OSS URL
        data = resp.read()
    if len(data) < 1000:
        raise RuntimeError(f"download too small: {url}")
    dest.write_bytes(data)


def _media_duration_sec(path: Path) -> float:
    if path.suffix.lower() == ".wav":
        try:
            with wave.open(str(path), "rb") as wf:
                rate = wf.getframerate()
                return wf.getnframes() / float(rate) if rate > 0 else 0.0
        except wave.Error:
            pass
    if shutil.which("ffprobe"):
        out = subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            text=True,
        ).strip()
        return float(out)
    return 0.0


def _concat_parts(parts: list[Path], out_wav: Path) -> None:
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg not found in PATH")
    list_file = TMP / "concat.txt"
    list_file.write_text(
        "\n".join(f"file '{p.resolve().as_posix()}'" for p in parts) + "\n",
        encoding="utf-8",
    )
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_file),
            "-ar",
            "16000",
            "-ac",
            "1",
            "-c:a",
            "pcm_s16le",
            str(out_wav),
        ],
        check=True,
        capture_output=True,
    )


def _wav_duration_sec(path: Path) -> float:
    with wave.open(str(path), "rb") as wf:
        rate = wf.getframerate()
        return wf.getnframes() / float(rate) if rate > 0 else 0.0


def fetch_source(spec: SourceSpec) -> dict[str, Any]:
    if TMP.exists():
        for p in TMP.glob("*"):
            if p.is_file():
                p.unlink()
    else:
        TMP.mkdir(parents=True, exist_ok=True)

    parts: list[Path] = []
    total = 0.0
    used_urls: list[str] = []
    for url in spec.fragment_urls:
        name = url.rsplit("/", 1)[-1]
        dest = TMP / name
        _download(url, dest)
        dur = _media_duration_sec(dest)
        parts.append(dest)
        used_urls.append(url)
        total += dur
        if total >= TARGET_MIN_SEC:
            break

    if total < 5.0:
        raise RuntimeError("insufficient_audio_downloaded")

    spec.out_wav.parent.mkdir(parents=True, exist_ok=True)
    _concat_parts(parts, spec.out_wav)
    duration_sec = round(_wav_duration_sec(spec.out_wav), 3)

    report = {
        "schema": "ko_shorts_web_speech_fetch_v1",
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "not_patient_data": True,
        "clinical_sim": spec.clinical_sim_member,
        "proxy_tier": spec.proxy_tier,
        "ok": True,
        "generated_at_utc": _utc_now(),
        "wav_path": _rel(spec.out_wav),
        "wav_bytes": spec.out_wav.stat().st_size,
        "duration_sec": duration_sec,
        "source": spec.key,
        "source_page": spec.source_page,
        "license": spec.license,
        "speaker_talk": spec.speaker_talk,
        "fragment_count": len(parts),
        "fragment_urls": used_urls,
        "reproduce": f"py scripts/fetch_ko_shorts_web_speech_wav_v1.py --source {spec.key}",
    }
    spec.out_meta.parent.mkdir(parents=True, exist_ok=True)
    spec.out_meta.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def fetch_youtube_edu() -> dict[str, Any]:
    from scripts.fetch_youtube_audio_clip_wav_v1 import fetch_youtube_clip_wav_v1

    ssot = json.loads(YOUTUBE_EDU_SSOT.read_text(encoding="utf-8-sig"))
    return fetch_youtube_clip_wav_v1(ssot, out_wav=YOUTUBE_EDU_WAV, out_meta=YOUTUBE_EDU_META)


def fetch_member_source(key: str) -> dict[str, Any]:
    if key == "youtube_edu":
        return fetch_youtube_edu()
    return fetch_source(SOURCES[key])


def _member_meta_path(key: str) -> Path | None:
    if key in SOURCES:
        return SOURCES[key].out_meta
    if key == "youtube_edu":
        return YOUTUBE_EDU_META
    return None


def _member_wav_path(key: str) -> Path | None:
    if key in SOURCES:
        return SOURCES[key].out_wav
    if key == "youtube_edu":
        return YOUTUBE_EDU_WAV
    return None


def build_clinical_sim_manifest_v1(member_reports: list[dict[str, Any]]) -> dict[str, Any]:
    """Bundle verified OSS proxy WAVs — not patient or clinical record data."""
    members = []
    for report in member_reports:
        source_key = str(report.get("source") or "")
        spec = SOURCES.get(source_key)
        proxy_tier = report.get("proxy_tier") or (spec.proxy_tier if spec else None)
        meta_path = _member_meta_path(source_key)
        members.append(
            {
                "source": report.get("source"),
                "proxy_tier": proxy_tier,
                "wav_path": report.get("wav_path"),
                "duration_sec": report.get("duration_sec"),
                "license": report.get("license"),
                "source_page": report.get("source_page"),
                "fetch_meta": _rel(meta_path) if meta_path else None,
            }
        )
    return {
        "schema": "ko_shorts_clinical_sim_manifest_v1",
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "not_patient_data": True,
        "clinical_sim": True,
        "clinical_sim_note": (
            "OSS/allowlisted YouTube proxy bundle for dialogue/read/education drift margin only; "
            "not AI-Hub counseling or real patient audio"
        ),
        "ok": True,
        "generated_at_utc": _utc_now(),
        "member_count": len(members),
        "members": members,
        "proxy_tiers": sorted({str(m.get("proxy_tier") or "") for m in members if m.get("proxy_tier")}),
        "reproduce": "py scripts/fetch_ko_shorts_web_speech_wav_v1.py --source clinical_sim",
    }


def write_clinical_sim_manifest(member_reports: list[dict[str, Any]]) -> dict[str, Any]:
    manifest = build_clinical_sim_manifest_v1(member_reports)
    CLINICAL_SIM_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    CLINICAL_SIM_MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def fetch_clinical_sim_bundle() -> dict[str, Any]:
    reports = [fetch_member_source(key) for key in CLINICAL_SIM_MEMBERS]
    return write_clinical_sim_manifest(reports)


def ensure_clinical_sim_manifest(*, refetch_missing: bool = False) -> dict[str, Any]:
    """Write manifest from disk meta when possible; fetch only if required."""
    if CLINICAL_SIM_MANIFEST.is_file() and not refetch_missing:
        return json.loads(CLINICAL_SIM_MANIFEST.read_text(encoding="utf-8-sig"))

    reports: list[dict[str, Any]] = []
    for key in CLINICAL_SIM_MEMBERS:
        meta_path = _member_meta_path(key)
        wav_path = _member_wav_path(key)
        if meta_path and meta_path.is_file():
            reports.append(json.loads(meta_path.read_text(encoding="utf-8-sig")))
        elif wav_path and wav_path.is_file():
            spec = SOURCES.get(key)
            reports.append(
                {
                    "source": key,
                    "proxy_tier": spec.proxy_tier if spec else "education_allowlist",
                    "wav_path": _rel(wav_path),
                    "duration_sec": round(_wav_duration_sec(wav_path), 3),
                    "license": spec.license if spec else "YouTube allowlist clip",
                    "source_page": spec.source_page if spec else str(YOUTUBE_EDU_SSOT),
                }
            )

    if len(reports) == len(CLINICAL_SIM_MEMBERS):
        return write_clinical_sim_manifest(reports)
    return fetch_clinical_sim_bundle()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--source",
        choices=["pansori", "deeply", "youtube_edu", "clinical_sim", "all"],
        default="all",
        help="OSS/allowlist speech; clinical_sim = full proxy bundle manifest",
    )
    args = ap.parse_args()

    if args.source == "clinical_sim":
        manifest = fetch_clinical_sim_bundle()
        print(
            json.dumps(
                {
                    "ok": True,
                    "clinical_sim": True,
                    "manifest": _rel(CLINICAL_SIM_MANIFEST),
                    "member_count": manifest.get("member_count"),
                    "members": [m.get("wav_path") for m in manifest.get("members") or []],
                },
                ensure_ascii=False,
            )
        )
        return 0

    if args.source == "youtube_edu":
        report = fetch_youtube_edu()
        print(
            json.dumps(
                {
                    "ok": True,
                    "source": "youtube_edu",
                    "wav_path": report["wav_path"],
                    "duration_sec": report["duration_sec"],
                    "proxy_tier": report.get("proxy_tier"),
                },
                ensure_ascii=False,
            )
        )
        return 0

    keys = list(SOURCES) if args.source == "all" else [args.source]
    results: list[dict[str, Any]] = []
    member_reports: list[dict[str, Any]] = []
    for key in keys:
        report = fetch_source(SOURCES[key])
        results.append(
            {
                "source": key,
                "wav_path": report["wav_path"],
                "duration_sec": report["duration_sec"],
                "license": report["license"],
                "fragment_count": report["fragment_count"],
                "proxy_tier": report["proxy_tier"],
            }
        )
        if SOURCES[key].clinical_sim_member:
            member_reports.append(report)

    if args.source == "all":
        member_reports.append(fetch_youtube_edu())
        results.append(
            {
                "source": "youtube_edu",
                "wav_path": member_reports[-1]["wav_path"],
                "duration_sec": member_reports[-1]["duration_sec"],
                "license": member_reports[-1].get("license"),
                "proxy_tier": member_reports[-1].get("proxy_tier"),
            }
        )

    if args.source == "all" and len(member_reports) == len(CLINICAL_SIM_MEMBERS):
        write_clinical_sim_manifest(member_reports)

    print(json.dumps({"ok": True, "sources": results}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
