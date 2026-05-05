#!/usr/bin/env python3
"""Build deterministic Sasang promotion candidate chain (v1~v9) in Track B.

This script does not auto-promote to Track A. It only emits reproducible
artifacts for human review and downstream gate evaluation.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_LENS = ART / "sasang_independent_lens_latest.json"
DEFAULT_GATE_STD = ART / "sasang_high_reliability_gate_latest.json"
DEFAULT_GATE_STRICT = ART / "sasang_high_reliability_gate_strict_latest.json"
DEFAULT_SWEEP_OUT = ART / "sasang_selector_sweep_latest.json"
DEFAULT_CHAIN_OUT = ART / "sasang12_promotion_candidate_chain_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _jread(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _decision_to_score(decision: str) -> float:
    d = str(decision or "").upper()
    if d == "PASS":
        return 1.0
    if d == "HOLD":
        return 0.5
    return 0.0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--lens", type=Path, default=DEFAULT_LENS)
    ap.add_argument("--gate-standard", type=Path, default=DEFAULT_GATE_STD)
    ap.add_argument("--gate-strict", type=Path, default=DEFAULT_GATE_STRICT)
    ap.add_argument("--sweep-out", type=Path, default=DEFAULT_SWEEP_OUT)
    ap.add_argument("--chain-out", type=Path, default=DEFAULT_CHAIN_OUT)
    args = ap.parse_args()

    for p in (args.lens, args.gate_standard, args.gate_strict):
        if not p.is_file():
            print(f"ERROR: required artifact missing: {p}")
            return 2

    lens = _jread(args.lens)
    gate_std = _jread(args.gate_standard)
    gate_strict = _jread(args.gate_strict)

    direction = float((lens.get("scores") or {}).get("direction_score") or 0.0)
    confidence = float((lens.get("scores") or {}).get("confidence") or 0.0)
    std_score = _decision_to_score(gate_std.get("decision"))
    strict_score = _decision_to_score(gate_strict.get("decision"))

    # Deterministic v1~v9 candidate sweep (Track B observation-only).
    base = (0.45 * confidence) + (0.35 * abs(direction)) + (0.20 * std_score)
    candidates: list[dict[str, Any]] = []
    for idx in range(1, 10):
        penalty = 0.03 * idx * (1.0 - strict_score)
        score = max(0.0, min(1.0, base - penalty))
        candidates.append(
            {
                "candidate_id": f"v{idx}",
                "selector_mode": "balanced_confidence_direction",
                "score": round(score, 6),
                "strict_gate_dependency": round(penalty, 6),
                "eligible_for_human_review": bool(score >= 0.25),
            }
        )

    winner = max(candidates, key=lambda x: x["score"])
    sweep = {
        "schema": "sasang_selector_sweep_v1",
        "generated_at_utc": _now(),
        "inputs": {
            "lens": str(args.lens.resolve()),
            "gate_standard": str(args.gate_standard.resolve()),
            "gate_strict": str(args.gate_strict.resolve()),
        },
        "track_wall": {
            "track_b_only": True,
            "a_track_autobind_forbidden": True,
            "promotion_to_a_track_allowed": False,
        },
        "candidates": candidates,
        "winner": winner,
    }
    chain = {
        "schema": "sasang12_promotion_candidate_chain_v1",
        "generated_at_utc": _now(),
        "version_range": "v1_to_v9",
        "status": "READY_FOR_GATE_EVAL",
        "winner_candidate_id": winner["candidate_id"],
        "winner_score": winner["score"],
        "candidate_count": len(candidates),
        "track_wall": {
            "track_b_only": True,
            "a_track_autobind_forbidden": True,
            "promotion_to_a_track_allowed": False,
        },
        "notes": [
            "This chain is a deterministic Track B selector sweep artifact.",
            "Any A-track promotion remains human-gated and forbidden by default.",
        ],
    }

    _write(args.sweep_out, sweep)
    _write(args.chain_out, chain)
    print(f"WROTE: {args.sweep_out}")
    print(f"WROTE: {args.chain_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
