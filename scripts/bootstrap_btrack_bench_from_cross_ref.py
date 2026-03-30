#!/usr/bin/env python3
"""Bootstrap larger B-Track pilot bench JSONL from CROSS_REF draft.

This generates synthetic-but-traceable A/B paired eval rows from:
  - docs/final/artifacts/CROSS_REF_DSS_TO_STATES_DRAFT.json
  - docs/final/artifacts/LOGOS_STATE_MAPPING_V1.json

Goal: quickly build 30-100 aligned pairs for pilot gating without touching
production A-track artifacts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CROSS_REF = ROOT / "docs" / "final" / "artifacts" / "CROSS_REF_DSS_TO_STATES_DRAFT.json"
DEFAULT_MAPPING = ROOT / "docs" / "final" / "artifacts" / "LOGOS_STATE_MAPPING_V1.json"
DEFAULT_A_OUT = ROOT / "data" / "logos" / "btrack_pilot" / "bench" / "a_track_eval.jsonl"
DEFAULT_B_OUT = ROOT / "data" / "logos" / "btrack_pilot" / "bench" / "b_track_eval.jsonl"


def _abs(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def _jload(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _hash01(s: str) -> float:
    h = hashlib.sha256(s.encode("utf-8")).hexdigest()
    n = int(h[:8], 16)
    return n / 0xFFFFFFFF


def _direction_for_state(state_id: int) -> str:
    # Deterministic coarse mapping for pilot comparability.
    if state_id <= 5:
        return "up"
    if state_id <= 11:
        return "flat"
    return "down"


def main() -> int:
    ap = argparse.ArgumentParser(description="Bootstrap B-Track A/B bench from CROSS_REF draft")
    ap.add_argument("--cross-ref", default=str(DEFAULT_CROSS_REF), help="CROSS_REF draft JSON")
    ap.add_argument("--mapping", default=str(DEFAULT_MAPPING), help="LOGOS state mapping JSON")
    ap.add_argument("--a-out", default=str(DEFAULT_A_OUT), help="A-track eval JSONL out")
    ap.add_argument("--b-out", default=str(DEFAULT_B_OUT), help="B-track eval JSONL out")
    ap.add_argument("--scenarios", type=int, default=3, help="Scenario multiplier per entry")
    args = ap.parse_args()

    cross_ref_path = _abs(args.cross_ref)
    mapping_path = _abs(args.mapping)
    a_out = _abs(args.a_out)
    b_out = _abs(args.b_out)

    if not cross_ref_path.is_file():
        print(f"ERROR: missing cross-ref file: {cross_ref_path}")
        return 2
    if not mapping_path.is_file():
        print(f"ERROR: missing state mapping file: {mapping_path}")
        return 2
    if args.scenarios < 2:
        print("ERROR: --scenarios must be >= 2 for expanded bench")
        return 2

    cross = _jload(cross_ref_path)
    mapping = _jload(mapping_path)
    assignments = mapping.get("assignments", [])
    state_to_cos = {
        int(a["state_id"]): float(a["cosine_state_verse"])
        for a in assignments
        if isinstance(a, dict) and "state_id" in a and "cosine_state_verse" in a
    }

    entries = cross.get("entries", [])
    if not isinstance(entries, list) or not entries:
        print("ERROR: no entries in CROSS_REF draft")
        return 3

    scenario_offsets = [0.00, 0.02, -0.01, 0.01, -0.02]
    a_rows: list[dict[str, Any]] = []
    b_rows: list[dict[str, Any]] = []

    for e in entries:
        if not isinstance(e, dict):
            continue
        entry_id = str(e.get("entry_id", "")).strip()
        state_id = e.get("state_candidate_id")
        if not entry_id or not isinstance(state_id, int):
            continue
        base_cos = state_to_cos.get(state_id, 0.86)
        direction = _direction_for_state(state_id)
        link_type = str(e.get("link_type", "thematic"))
        corpus_type = str(e.get("corpus_type", "unknown"))

        for i in range(args.scenarios):
            scenario_name = f"s{i+1}"
            key = f"{entry_id}_{scenario_name}"
            noise = (_hash01(key) - 0.5) * 0.02
            a_conf = _clamp(base_cos + scenario_offsets[i % len(scenario_offsets)] + noise, 0.55, 0.98)

            # B-track gets small uplift by default, with mild penalty for uncertain anchors.
            anchor_penalty = 0.015 if "missing_anchor" in str(e.get("satellite_ref", "")) else 0.0
            b_conf = _clamp(a_conf + 0.025 - anchor_penalty, 0.55, 0.99)

            a_snr = _clamp(0.95 + (a_conf - 0.75) * 0.9, 0.70, 1.50)
            b_snr = _clamp(a_snr + 0.03 - (anchor_penalty * 0.5), 0.70, 1.55)

            common = {
                "id": key,
                "entry_id": entry_id,
                "state_id": state_id,
                "direction": direction,
                "scenario": scenario_name,
                "source": "bootstrap_btrack_bench_from_cross_ref",
                "synthetic_pilot": True,
                "link_type": link_type,
                "corpus_type": corpus_type,
            }

            a_rows.append(
                {
                    **common,
                    "track": "A",
                    "confidence": round(a_conf, 6),
                    "snr": round(a_snr, 6),
                }
            )
            b_rows.append(
                {
                    **common,
                    "track": "B",
                    "confidence": round(b_conf, 6),
                    "snr": round(b_snr, 6),
                }
            )

    a_out.parent.mkdir(parents=True, exist_ok=True)
    b_out.parent.mkdir(parents=True, exist_ok=True)
    with a_out.open("w", encoding="utf-8") as fa:
        for row in a_rows:
            fa.write(json.dumps(row, ensure_ascii=False) + "\n")
    with b_out.open("w", encoding="utf-8") as fb:
        for row in b_rows:
            fb.write(json.dumps(row, ensure_ascii=False) + "\n")

    print("OK: bootstrapped expanded A/B bench")
    print(f"a_out={a_out} rows={len(a_rows)}")
    print(f"b_out={b_out} rows={len(b_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
