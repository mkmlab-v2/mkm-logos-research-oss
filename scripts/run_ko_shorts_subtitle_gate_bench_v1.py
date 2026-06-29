#!/usr/bin/env python3
"""Run Netflix v16 + shorts v28 subtitle gates on STT spike corpora [HYPO]."""

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

from scripts.ko_shorts_subtitle_gate_lib_v1 import (  # noqa: E402
    PROFILE_NETFLIX_V16,
    PROFILE_SHORTS_V28,
    PROFILES,
    evaluate_subtitle_gate_v1,
    refine_segments_for_profile_v1,
)

DEFAULT_OUT = ROOT / "reports/ko_shorts_subtitle_gate_bench_v1_latest.json"
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


def _base_segments(doc: dict[str, Any]) -> list[dict[str, Any]]:
    return list(doc.get("p1_segments") or doc.get("p0_segments") or [])


def build_gate_bench_report() -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    for case_id, path in SPIKE_CASES:
        if not path.is_file():
            continue
        doc = _read_json(path)
        base = _base_segments(doc)
        if not base:
            continue
        profile_results: dict[str, Any] = {}
        for key, profile in PROFILES.items():
            refined = refine_segments_for_profile_v1(base, profile)
            gate = evaluate_subtitle_gate_v1(refined, profile)
            profile_results[key] = {
                "gate": gate,
                "segment_count": len(refined),
                "sample_lines": [s.get("text") for s in refined[:3]],
            }
        cases.append(
            {
                "case_id": case_id,
                "spike_json": _rel(path),
                "wav_source": doc.get("wav_source"),
                "base_segment_count": len(base),
                "profiles": profile_results,
            }
        )

    netflix_pass = sum(
        1 for c in cases if (c.get("profiles") or {}).get(PROFILE_NETFLIX_V16, {}).get("gate", {}).get("gate_pass")
    )
    shorts_pass = sum(
        1 for c in cases if (c.get("profiles") or {}).get(PROFILE_SHORTS_V28, {}).get("gate", {}).get("gate_pass")
    )
    return {
        "schema": "ko_shorts_subtitle_gate_bench_v1",
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "generated_at_utc": _utc_now(),
        "profiles": {k: {"max_chars": p.max_chars, "cps_target": p.cps_target} for k, p in PROFILES.items()},
        "case_count": len(cases),
        "netflix_v16_pass_count": netflix_pass,
        "shorts_v28_pass_count": shorts_pass,
        "cases": cases,
        "reproduce": "py scripts/run_ko_shorts_subtitle_gate_bench_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    report = build_gate_bench_report()
    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "out": _rel(out),
                "case_count": report["case_count"],
                "netflix_v16_pass": report["netflix_v16_pass_count"],
                "shorts_v28_pass": report["shorts_v28_pass_count"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
