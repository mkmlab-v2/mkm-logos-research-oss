#!/usr/bin/env python3
"""Compare P0 semantic vs P1 aligned timing across TTS bench + web speech sources [HYPO]."""

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

DEFAULT_OUT = ROOT / "reports/ko_shorts_timing_compare_v1_latest.json"
SPIKE_CLI = ROOT / "scripts/run_ko_shorts_stt_timing_spike_v1.py"
FETCH_CLI = ROOT / "scripts/fetch_ko_shorts_web_speech_wav_v1.py"
CLINICAL_SIM_MANIFEST = ROOT / "reports/ko_shorts_clinical_sim_manifest_v1_latest.json"
BENCH_WAV = ROOT / "reports/audio/ko_shorts_timing_bench_v1.wav"
BENCH_BUILDER = ROOT / "scripts/build_ko_shorts_timing_bench_wav_v1.py"

CASES: list[dict[str, str]] = [
    {
        "case_id": "tts_bench",
        "label": "supertonic TTS bench",
        "wav": "reports/audio/ko_shorts_timing_bench_v1.wav",
        "spike_out": "reports/ko_shorts_stt_timing_bench_v1_latest.json",
        "kind": "synthetic",
    },
    {
        "case_id": "web_pansori",
        "label": "Pansori TEDxKR web (clinical_sim proxy)",
        "wav": "reports/audio/ko_shorts_web_pansori_tedxkr_v1.wav",
        "spike_out": "reports/ko_shorts_stt_timing_web_pansori_v1_latest.json",
        "kind": "clinical_sim_proxy",
        "proxy_bundle": "clinical_sim",
        "proxy_tier": "interview",
        "not_patient_data": "true",
    },
    {
        "case_id": "web_deeply",
        "label": "Deeply read speech web (clinical_sim proxy)",
        "wav": "reports/audio/ko_shorts_web_deeply_read_v1.wav",
        "spike_out": "reports/ko_shorts_stt_timing_web_deeply_v1_latest.json",
        "kind": "clinical_sim_proxy",
        "proxy_bundle": "clinical_sim",
        "proxy_tier": "read",
        "not_patient_data": "true",
    },
    {
        "case_id": "web_youtube_edu",
        "label": "YouTube TEDxKR allowlist clip (clinical_sim proxy)",
        "wav": "reports/audio/ko_shorts_web_youtube_edu_v1.wav",
        "spike_out": "reports/ko_shorts_stt_timing_web_youtube_edu_v1_latest.json",
        "kind": "clinical_sim_proxy",
        "proxy_bundle": "clinical_sim",
        "proxy_tier": "education_allowlist",
        "not_patient_data": "true",
    },
]

CLINICAL_SIM_CASE_IDS = frozenset({"web_pansori", "web_deeply", "web_youtube_edu"})


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, cwd=ROOT)


def _ensure_bench_wav() -> None:
    if BENCH_WAV.is_file():
        return
    _run(["py", str(BENCH_BUILDER)])


def _ensure_clinical_sim_bundle() -> None:
    from scripts.fetch_ko_shorts_web_speech_wav_v1 import ensure_clinical_sim_manifest

    ensure_clinical_sim_manifest(refetch_missing=False)


def _run_spike(wav: Path, out_json: Path) -> dict[str, Any]:
    out_json.parent.mkdir(parents=True, exist_ok=True)
    _run(
        [
            "py",
            str(SPIKE_CLI),
            "--wav",
            str(wav),
            "--out",
            str(out_json),
            "--srt-out",
            str(out_json.with_suffix(".srt")),
        ]
    )
    return _read_json(out_json)


def _summarize_spike(case: dict[str, str], spike: dict[str, Any]) -> dict[str, Any]:
    drift = dict(spike.get("drift_vs_proportional") or {})
    p0 = list(spike.get("p0_segments") or [])
    p1 = list(spike.get("p1_segments") or [])
    return {
        "case_id": case["case_id"],
        "label": case["label"],
        "kind": case["kind"],
        "proxy_bundle": case.get("proxy_bundle"),
        "proxy_tier": case.get("proxy_tier"),
        "not_patient_data": case.get("not_patient_data") == "true",
        "wav_source": spike.get("wav_source") or case["wav"],
        "duration_sec": round(
            max(
                (
                    float(s.get("duration_sec") or 0.0)
                    for s in p0 + p1
                ),
                default=0.0,
            ),
            3,
        ),
        "aligned_word_count": spike.get("aligned_word_count"),
        "p0_segment_count": spike.get("p0_segment_count"),
        "p1_segment_count": spike.get("p1_segment_count"),
        "p0_mode": spike.get("p0_mode") or "semantic_chunk_ko_v1_proportional",
        "p1_mode": "aligned_token_pause_max_chars",
        "drift_vs_proportional": drift,
        "p0_sample_texts": [str(s.get("text") or "") for s in p0[:3]],
        "p1_sample_texts": [str(s.get("text") or "") for s in p1[:3]],
        "spike_json": case["spike_out"],
    }


def _clinical_sim_spectrum(cases: list[dict[str, Any]]) -> dict[str, Any] | None:
    sim = [c for c in cases if c.get("proxy_bundle") == "clinical_sim"]
    if not sim:
        return None
    rows = []
    for c in sim:
        drift = dict(c.get("drift_vs_proportional") or {})
        rows.append(
            {
                "case_id": c.get("case_id"),
                "proxy_tier": c.get("proxy_tier"),
                "start_drift_ms_mean": drift.get("start_drift_ms_mean"),
                "end_drift_ms_mean": drift.get("end_drift_ms_mean"),
            }
        )
    start_vals = [r["start_drift_ms_mean"] for r in rows if r.get("start_drift_ms_mean") is not None]
    end_vals = [r["end_drift_ms_mean"] for r in rows if r.get("end_drift_ms_mean") is not None]
    return {
        "bundle": "clinical_sim",
        "not_patient_data": True,
        "member_count": len(rows),
        "members": rows,
        "start_drift_ms_mean_range": [min(start_vals), max(start_vals)] if start_vals else None,
        "end_drift_ms_mean_range": [min(end_vals), max(end_vals)] if end_vals else None,
        "interpretation": (
            "interview/spontaneous proxy tends higher P0-P1 gap than read-aloud proxy; "
            "gap metric only — not clinical sync pass"
        ),
    }


def build_compare_report(*, cases: list[dict[str, Any]]) -> dict[str, Any]:
    spectrum = _clinical_sim_spectrum(cases)
    report = {
        "schema": "ko_shorts_timing_compare_v1",
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "generated_at_utc": _utc_now(),
        "p0_authority": "semantic_chunk_ko_v1 + proportional timestamps (whisper segments)",
        "p1_authority": "aligned word tokens + pause/max_chars chunking",
        "drift_note": "drift_vs_proportional = |P0-P1| boundary gap metric; not sync-quality pass",
        "cases": cases,
        "reproduce": "py scripts/run_ko_shorts_timing_compare_v1.py",
    }
    if spectrum:
        report["clinical_sim_spectrum"] = spectrum
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--skip-fetch", action="store_true")
    ap.add_argument("--skip-bench-build", action="store_true")
    ap.add_argument(
        "--cases",
        default="all",
        help="comma list: tts_bench,web_pansori,web_deeply,web_youtube_edu,clinical_sim or all",
    )
    args = ap.parse_args()

    selected = {c["case_id"] for c in CASES}
    if args.cases == "clinical_sim":
        selected = set(CLINICAL_SIM_CASE_IDS)
    elif args.cases != "all":
        selected = {x.strip() for x in args.cases.split(",") if x.strip()}

    if not args.skip_bench_build and "tts_bench" in selected:
        _ensure_bench_wav()
    if not args.skip_fetch and selected & CLINICAL_SIM_CASE_IDS:
        _ensure_clinical_sim_bundle()

    summaries: list[dict[str, Any]] = []
    for case in CASES:
        if case["case_id"] not in selected:
            continue
        wav = ROOT / case["wav"]
        spike_out = ROOT / case["spike_out"]
        if not wav.is_file():
            print(json.dumps({"ok": False, "error": "wav_missing", "path": _rel(wav)}), file=sys.stderr)
            return 1
        spike = _run_spike(wav, spike_out)
        summaries.append(_summarize_spike(case, spike))

    report = build_compare_report(cases=summaries)
    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "out": _rel(out),
                "case_count": len(summaries),
                "drift_summary": [
                    {
                        "case_id": s["case_id"],
                        "proxy_tier": s.get("proxy_tier"),
                        "start_drift_ms_mean": (s.get("drift_vs_proportional") or {}).get(
                            "start_drift_ms_mean"
                        ),
                        "end_drift_ms_mean": (s.get("drift_vs_proportional") or {}).get(
                            "end_drift_ms_mean"
                        ),
                    }
                    for s in summaries
                ],
                "clinical_sim_spectrum": (report.get("clinical_sim_spectrum") or {}).get(
                    "start_drift_ms_mean_range"
                ),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
