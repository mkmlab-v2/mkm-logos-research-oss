#!/usr/bin/env python3
"""Pause gap × max_chars grid for ko shorts P1 chunking [HYPO]."""

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

from scripts.ko_shorts_alignment_backend_lib_v1 import (  # noqa: E402
    BACKEND_FASTER_WHISPER,
    extract_words_for_backend_v1,
)
from scripts.ko_shorts_stt_timing_lib_v1 import (  # noqa: E402
    chunk_aligned_words_v1,
    compute_timing_drift_ms_v1,
    segments_proportional_from_words_v1,
)
from scripts.ko_shorts_subtitle_gate_lib_v1 import (  # noqa: E402
    PROFILE_NETFLIX_V16,
    PROFILES,
    evaluate_subtitle_gate_v1,
    refine_segments_for_profile_v1,
)

DEFAULT_OUT = ROOT / "reports/ko_shorts_pause_chunk_grid_v1_latest.json"
DEFAULT_FIXTURE = ROOT / "tests/fixtures/ko_shorts_aligned_words_spike_v1.json"

CASES = [
    {"case_id": "web_pansori", "wav": "reports/audio/ko_shorts_web_pansori_tedxkr_v1.wav"},
    {"case_id": "web_deeply", "wav": "reports/audio/ko_shorts_web_deeply_read_v1.wav"},
    {"case_id": "web_youtube_edu", "wav": "reports/audio/ko_shorts_web_youtube_edu_v1.wav"},
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


def _load_words_for_case(case: dict[str, str], *, from_fixture: bool) -> tuple[list[dict[str, Any]], str, str | None]:
    if from_fixture:
        doc = _read_json(DEFAULT_FIXTURE)
        return list(doc.get("words") or []), str(doc.get("wav_source") or "fixture"), None
    wav = ROOT / case["wav"]
    if not wav.is_file():
        return [], case["wav"], "wav_missing"
    words, err = extract_words_for_backend_v1(BACKEND_FASTER_WHISPER, wav, model_name="small", language="ko")
    return words, case["wav"], err


def _eval_grid_cell(
    words: list[dict[str, Any]],
    *,
    pause_gap_sec: float,
    max_chars: int,
    profile_key: str,
) -> dict[str, Any]:
    profile = PROFILES[profile_key]
    p1 = chunk_aligned_words_v1(words, max_chars=max_chars, pause_gap_sec=pause_gap_sec)
    p0 = segments_proportional_from_words_v1(words)
    drift = compute_timing_drift_ms_v1(p0, p1)
    subtitle_segments = refine_segments_for_profile_v1(p1, profile, two_pass=True)
    gate = evaluate_subtitle_gate_v1(subtitle_segments, profile)
    return {
        "pause_gap_sec": pause_gap_sec,
        "max_chars": max_chars,
        "profile": profile_key,
        "p1_segment_count": len(p1),
        "subtitle_segment_count": len(subtitle_segments),
        "gate_pass": bool(gate.get("gate_pass")),
        "gate": gate,
        "start_drift_ms_mean": (drift or {}).get("start_drift_ms_mean"),
        "end_drift_ms_mean": (drift or {}).get("end_drift_ms_mean"),
    }


def _pick_recommendation(rows: list[dict[str, Any]]) -> dict[str, Any]:
    passing = [r for r in rows if r.get("gate_pass")]
    pool = passing or rows
    best = min(
        pool,
        key=lambda r: (
            0 if r.get("gate_pass") else 1,
            float(r.get("start_drift_ms_mean") or 99999.0),
            -int(r.get("subtitle_segment_count") or 0),
        ),
    )
    return {
        "pause_gap_sec": best.get("pause_gap_sec"),
        "max_chars": best.get("max_chars"),
        "profile": best.get("profile"),
        "gate_pass": best.get("gate_pass"),
        "rationale": "gate_pass first, then min start_drift_ms_mean",
    }


def build_pause_chunk_grid_v1(
    *,
    cases: list[dict[str, str]],
    pause_gaps: tuple[float, ...],
    max_chars_list: tuple[int, ...],
    profile_key: str,
    from_fixture: bool,
) -> dict[str, Any]:
    case_rows: list[dict[str, Any]] = []
    for case in cases:
        words, wav_source, err = _load_words_for_case(case, from_fixture=from_fixture)
        if err or not words:
            case_rows.append({"case_id": case["case_id"], "ok": False, "error": err or "no_words"})
            continue
        grid_rows = [
            _eval_grid_cell(
                words,
                pause_gap_sec=gap,
                max_chars=mc,
                profile_key=profile_key,
            )
            for gap in pause_gaps
            for mc in max_chars_list
        ]
        case_rows.append(
            {
                "case_id": case["case_id"],
                "ok": True,
                "wav_source": wav_source,
                "word_count": len(words),
                "grid": grid_rows,
                "recommendation": _pick_recommendation(grid_rows),
            }
        )

    global_pass = [r["recommendation"] for r in case_rows if r.get("ok")]
    consensus = _pick_recommendation(
        [
            {
                "pause_gap_sec": rec.get("pause_gap_sec"),
                "max_chars": rec.get("max_chars"),
                "profile": rec.get("profile"),
                "gate_pass": rec.get("gate_pass"),
                "start_drift_ms_mean": 0.0,
                "subtitle_segment_count": 0,
            }
            for rec in global_pass
        ]
    ) if global_pass else {}

    return {
        "schema": "ko_shorts_pause_chunk_grid_v1",
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "generated_at_utc": _utc_now(),
        "profile_default": profile_key,
        "pause_gaps": list(pause_gaps),
        "max_chars_list": list(max_chars_list),
        "from_fixture": from_fixture,
        "cases": case_rows,
        "consensus_recommendation": consensus,
        "reproduce": "py scripts/run_ko_shorts_pause_chunk_grid_v1.py --cases clinical_sim",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--cases", default="clinical_sim", help="clinical_sim | all | comma case ids")
    ap.add_argument("--pause-gaps", default="0.3,0.4,0.5")
    ap.add_argument("--max-chars-list", default="16,28")
    ap.add_argument("--profile", default=PROFILE_NETFLIX_V16, choices=list(PROFILES))
    ap.add_argument("--from-fixture", action="store_true", help="offline: use aligned words fixture")
    args = ap.parse_args()

    if args.cases == "all":
        selected = CASES
    elif args.cases == "clinical_sim":
        selected = CASES
    else:
        ids = {x.strip() for x in args.cases.split(",") if x.strip()}
        selected = [c for c in CASES if c["case_id"] in ids]

    pause_gaps = tuple(float(x.strip()) for x in args.pause_gaps.split(",") if x.strip())
    max_chars_list = tuple(int(x.strip()) for x in args.max_chars_list.split(",") if x.strip())

    report = build_pause_chunk_grid_v1(
        cases=selected,
        pause_gaps=pause_gaps,
        max_chars_list=max_chars_list,
        profile_key=args.profile,
        from_fixture=args.from_fixture,
    )
    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "out": _rel(out),
                "case_count": len(report.get("cases") or []),
                "consensus": report.get("consensus_recommendation"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
