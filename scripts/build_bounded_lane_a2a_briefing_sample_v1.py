#!/usr/bin/env python3
"""Build fixed A2A briefing sample for bounded lane shadow loop ([HYPO] B-track).

  py scripts/build_bounded_lane_a2a_briefing_sample_v1.py --lane infra

Output: docs/final/artifacts/fixtures/bounded_lane_a2a_briefing_sample_v1.json
Also refreshes: docs/final/artifacts/mkm_inter_agent_dialogue_mock_summary_latest.json
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_OUT = ROOT / "docs/final/artifacts/fixtures/bounded_lane_a2a_briefing_sample_v1.json"
MOCK_SUMMARY = ROOT / "docs/final/artifacts/mkm_inter_agent_dialogue_mock_summary_latest.json"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_mkm_inter_agent_dialogue_mock_v1 import run_dialogue  # noqa: E402


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _briefing_one_line(dialogue: dict[str, Any]) -> str:
    parts: list[str] = []
    for row in dialogue.get("transcript") or []:
        role = str(row.get("role") or "?")
        plain = str(row.get("internal_plaintext") or "")
        snippet = plain[:120].replace("\n", " ").strip()
        if snippet:
            parts.append(f"{role}: {snippet}")
    text = " | ".join(parts)
    return text[:480] if len(text) > 480 else text


def build_sample(*, lane: str, turns: int = 2) -> dict[str, Any]:
    dialogue = run_dialogue(turns=max(2, turns), routing_profile="track_a_promoted", scenario="trading")
    peer = (
        ROOT / f"docs/final/artifacts/a2a_tier3_cursor_wire_handoff_brief_{lane}_v1_latest.md"
    )
    peer_path = peer.relative_to(ROOT).as_posix() if peer.is_file() else None
    slim_transcript = []
    for row in dialogue.get("transcript") or []:
        slim_transcript.append(
            {
                "turn": row.get("turn"),
                "role": row.get("role"),
                "wire_only": row.get("wire_only"),
                "compress_http_status": (row.get("compress") or {}).get("http_status"),
                "trust_packet_redacted": row.get("trust_packet_redacted"),
            }
        )
    return {
        "schema": "bounded_lane_a2a_briefing_sample_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "classification": "INTERNAL_ONLY",
        "lane": lane,
        "peer_handoff_pointer": peer_path,
        "briefing_one_line": _briefing_one_line(dialogue),
        "dialogue_mock_summary": {
            "schema": dialogue.get("schema"),
            "all_compress_ok": dialogue.get("all_compress_ok"),
            "all_expand_ok": dialogue.get("all_expand_ok"),
            "turns_recorded": dialogue.get("turns_recorded"),
            "boundary_ack": dialogue.get("boundary_ack"),
            "transcript": slim_transcript,
        },
        "reproduce": f"py scripts/build_bounded_lane_a2a_briefing_sample_v1.py --lane {lane}",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--lane", default="infra", choices=["ms", "oracle", "infra", "design", "ops"])
    ap.add_argument("--turns", type=int, default=2)
    ap.add_argument("--out", type=Path, default=FIXTURE_OUT)
    args = ap.parse_args()

    sample = build_sample(lane=args.lane.strip().lower(), turns=args.turns)
    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(sample, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    full_dialogue = run_dialogue(
        turns=max(2, args.turns), routing_profile="track_a_promoted", scenario="trading"
    )
    MOCK_SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    MOCK_SUMMARY.write_text(
        json.dumps(full_dialogue, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print(
        json.dumps(
            {
                "ok": True,
                "out": out.relative_to(ROOT).as_posix(),
                "mock_summary": MOCK_SUMMARY.relative_to(ROOT).as_posix(),
                "briefing_one_line": sample["briefing_one_line"][:120],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
