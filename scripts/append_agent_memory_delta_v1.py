#!/usr/bin/env python3
"""Append compressed agent memory delta to JSONL store."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_CENTRAL = ROOT / "docs" / "final" / "CENTRAL_AGENT_MEMORY_V1.md"
DEFAULT_CONTEXT = ART / "agent_memory_current_context_v1_latest.json"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _tail_text(path: Path, max_chars: int = 300) -> str:
    if not path.is_file():
        return "no_central_memory_file"
    text = path.read_text(encoding="utf-8-sig", errors="replace").strip()
    if not text:
        return "empty_central_memory"
    return text[-max_chars:].replace("\n", " ")


def _has_any(text: str, needles: list[str]) -> bool:
    t = text.lower()
    return any(n in t for n in needles)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--memory-jsonl", type=Path, default=ART / "agent_memory_deltas_v1.jsonl")
    ap.add_argument("--write-combined", action="store_true")
    ap.add_argument("--central-memory-md", type=Path, default=DEFAULT_CENTRAL)
    ap.add_argument("--mission", default="session_auto_capture")
    ap.add_argument("--state", default="session_end")
    ap.add_argument("--risk", default="unknown")
    ap.add_argument("--next", default="resume_from_recent_delta")
    ap.add_argument("--track", choices=("A", "B"), default="B")
    ap.add_argument("--source", default="cursor_session_end_hook")
    ap.add_argument("--context-json", type=Path, default=DEFAULT_CONTEXT)
    ap.add_argument("--track-memory-jsonl-a", type=Path, default=ART / "agent_memory_deltas_track_a_v1.jsonl")
    ap.add_argument("--track-memory-jsonl-b", type=Path, default=ART / "agent_memory_deltas_track_b_v1.jsonl")
    ap.add_argument("--repro-cmd", default="")
    args = ap.parse_args()

    evidence = [str(args.central_memory_md).replace("\\", "/")] if args.central_memory_md.is_file() else []
    evidence_exists_all = all(Path(p).is_file() for p in evidence) if evidence else False

    merged_text = " ".join([str(args.mission), str(args.state), str(args.next), str(args.risk)]).lower()
    track = str(args.track)
    track_conflict = False
    if track == "A":
        track_conflict = _has_any(merged_text, ["research", "b-track", "hypo"])
    elif track == "B":
        track_conflict = _has_any(merged_text, ["production", "live_trading", "deploy_now"])

    policy_conflict = _has_any(merged_text, ["auto_bridge", "auto_live", "force_promotion"])
    has_conflict = track_conflict or policy_conflict

    confidence = "A"
    if (not evidence_exists_all) or has_conflict:
        confidence = "C"

    repro_cmd = str(args.repro_cmd).strip()
    reproducibility_score = 1 if repro_cmd else 0

    row = {
        "schema": "agent_memory_delta_v1",
        "ts_utc": _iso_now(),
        "mission": str(args.mission),
        "state": str(args.state),
        "evidence_path": evidence,
        "risk": str(args.risk),
        "next": str(args.next),
        "track": str(args.track),
        "confidence": confidence,
        "source": str(args.source),
        "repro_cmd": repro_cmd,
        "reproducibility_score": reproducibility_score,
        "evidence_exists_all": evidence_exists_all,
        "conflict_flags": {
            "track_conflict": track_conflict,
            "policy_conflict": policy_conflict,
            "has_conflict": has_conflict,
        },
        "summary_5line": [
            f"mission={args.mission}",
            f"state={args.state}",
            f"risk={args.risk}",
            f"next={args.next}",
            f"central_tail={_tail_text(args.central_memory_md)}",
        ],
    }

    if args.write_combined:
        args.memory_jsonl.parent.mkdir(parents=True, exist_ok=True)
        with args.memory_jsonl.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    # Physical split storage to prevent A/B track mixing.
    track_path = args.track_memory_jsonl_a if str(args.track) == "A" else args.track_memory_jsonl_b
    track_path.parent.mkdir(parents=True, exist_ok=True)
    with track_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    args.context_json.parent.mkdir(parents=True, exist_ok=True)
    args.context_json.write_text(
        json.dumps(
            {
                "schema": "agent_memory_current_context_v1",
                "updated_at_utc": _iso_now(),
                "context_3line": [
                    f"mission={row['mission']} track={row['track']}",
                    f"state={row['state']} risk={row['risk']}",
                    f"next={row['next']} confidence={row['confidence']} conflict={has_conflict}",
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "ok": True,
                "combined_written": bool(args.write_combined),
                "memory_jsonl": str(args.memory_jsonl),
                "track_memory_jsonl": str(track_path),
                "confidence": confidence,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
