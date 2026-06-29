#!/usr/bin/env python3
"""Bench semantic_chunk_ko_v1 vs KSS fast (+ optional KSSDS) on STT corpora [HYPO]."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ko_shorts_segment_backend_lib_v1 import (  # noqa: E402
    BACKEND_KSSDS,
    BACKEND_KSS_FAST,
    BACKEND_SEMANTIC,
    compare_backends_on_text_v1,
)

DEFAULT_OUT = ROOT / "reports/ko_shorts_segment_backend_bench_v1_latest.json"
DEFAULT_CASES = [
    {
        "case_id": "fixture_orphan_stt",
        "label": "orphan prefix/ending STT fixture",
        "text": "첫째, 잘한 것. 둘째, 개선할 점. 오늘 회고 문화를 짚어 줍니다.",
        "duration_sec": 8.0,
    },
    {
        "case_id": "fixture_no_punct_stt",
        "label": "low punctuation STT style",
        "text": (
            "저 식당 음식이 정말 맛있나봐요 아 저기요 삼계탕만 파는 식당인데 "
            "항상 사람들이 많아요 우리 회사 근처에 저런 유명한 식당이 있었네요"
        ),
        "duration_sec": 12.0,
    },
]

SPIKE_CASES = [
    ("web_pansori", ROOT / "reports/ko_shorts_stt_timing_web_pansori_v1_latest.json"),
    ("web_deeply", ROOT / "reports/ko_shorts_stt_timing_web_deeply_v1_latest.json"),
    ("web_youtube_edu", ROOT / "reports/ko_shorts_stt_timing_web_youtube_edu_v1_latest.json"),
    ("tts_bench", ROOT / "reports/ko_shorts_stt_timing_bench_v1_latest.json"),
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _text_from_spike(doc: dict[str, Any]) -> str:
    words = doc.get("words")
    if isinstance(words, list) and words:
        return " ".join(str(w.get("word") or "").strip() for w in words if str(w.get("word") or "").strip())
    p0 = doc.get("p0_segments") or doc.get("p1_segments") or []
    return " ".join(str(s.get("text") or "").strip() for s in p0 if str(s.get("text") or "").strip())


def _duration_from_spike(doc: dict[str, Any]) -> float | None:
    segs = list(doc.get("p1_segments") or doc.get("p0_segments") or [])
    if not segs:
        return None
    try:
        from scripts.media_stt_transcription_lib_v1 import parse_timestamp_seconds

        ends = [parse_timestamp_seconds(str(s.get("end") or "00:00:00.00")) for s in segs]
        return max(ends) if ends else None
    except Exception:
        return None


def load_bench_cases(*, include_spikes: bool = True) -> list[dict[str, Any]]:
    cases = [dict(c) for c in DEFAULT_CASES]
    if not include_spikes:
        return cases
    for case_id, path in SPIKE_CASES:
        if not path.is_file():
            continue
        doc = _read_json(path)
        text = _text_from_spike(doc)
        if not text:
            continue
        cases.append(
            {
                "case_id": case_id,
                "label": f"STT spike corpus {case_id}",
                "text": text,
                "duration_sec": _duration_from_spike(doc),
                "spike_json": _rel(path),
            }
        )
    return cases


def build_bench_report(
    *,
    cases: list[dict[str, Any]],
    max_chars: int,
    include_kssds: bool,
) -> dict[str, Any]:
    backends = (BACKEND_SEMANTIC, BACKEND_KSS_FAST)
    if include_kssds:
        backends = (BACKEND_SEMANTIC, BACKEND_KSS_FAST, BACKEND_KSSDS)

    bench_cases: list[dict[str, Any]] = []
    kssds_errors: list[str] = []
    for case in cases:
        comparison = compare_backends_on_text_v1(
            str(case["text"]),
            duration_sec=case.get("duration_sec"),
            max_chars=max_chars,
            backends=backends,
        )
        kssds = comparison.get(BACKEND_KSSDS) or {}
        if kssds.get("error"):
            kssds_errors.append(str(kssds["error"]))
        semantic_lines = (comparison.get(BACKEND_SEMANTIC) or {}).get("lines") or []
        kss_lines = (comparison.get(BACKEND_KSS_FAST) or {}).get("lines") or []
        bench_cases.append(
            {
                "case_id": case["case_id"],
                "label": case.get("label"),
                "duration_sec": case.get("duration_sec"),
                "spike_json": case.get("spike_json"),
                "text_chars": len(str(case["text"])),
                "backends": comparison,
                "delta_kss_minus_semantic_line_count": len(kss_lines) - len(semantic_lines),
            }
        )

    return {
        "schema": "ko_shorts_segment_backend_bench_v1",
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "generated_at_utc": _utc_now(),
        "max_chars": max_chars,
        "netflix_max_chars": 16,
        "netflix_cps_target": 12.0,
        "backends_tested": list(backends),
        "kssds_status": (
            "unavailable"
            if kssds_errors
            else ("not_requested" if not include_kssds else "ok")
        ),
        "kssds_error_sample": kssds_errors[0] if kssds_errors else None,
        "cases": bench_cases,
        "reproduce": "py scripts/run_ko_shorts_segment_backend_bench_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--max-chars", type=int, default=28)
    ap.add_argument("--include-kssds", action="store_true")
    ap.add_argument("--fixtures-only", action="store_true")
    args = ap.parse_args()

    cases = load_bench_cases(include_spikes=not args.fixtures_only)
    report = build_bench_report(
        cases=cases,
        max_chars=args.max_chars,
        include_kssds=args.include_kssds,
    )
    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    summary = {
        "ok": True,
        "out": _rel(out),
        "case_count": len(report["cases"]),
        "kssds_status": report["kssds_status"],
        "semantic_vs_kss_line_delta": [
            {
                "case_id": c["case_id"],
                "delta": c["delta_kss_minus_semantic_line_count"],
            }
            for c in report["cases"]
        ],
    }
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
