#!/usr/bin/env python3
"""Update anchor evidence slots from CROSS_REF structural evidence.

This script promotes selected/provisional slots to verified when:
- state_id exists in CROSS_REF_DSS_TO_STATES_DRAFT entries (state_candidate_id)
- evidence_ref is present
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SLOTS = ROOT / "data" / "logos" / "btrack_pilot" / "bench" / "btrack_anchor_evidence_slots.jsonl"
CROSS_REF = ROOT / "docs" / "final" / "artifacts" / "CROSS_REF_DSS_TO_STATES_DRAFT.json"
OUT = ROOT / "data" / "logos" / "btrack_pilot" / "bench" / "btrack_anchor_evidence_slots.jsonl"


def _abs(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if isinstance(obj, dict):
                out.append(obj)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Promote anchor evidence slots to verified from CROSS_REF")
    ap.add_argument("--slots", default=str(SLOTS))
    ap.add_argument("--cross-ref", default=str(CROSS_REF))
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--strength", type=float, default=0.85, help="anchor_strength for promoted slots")
    ap.add_argument("--state-ids", default="", help="Optional comma-separated state_ids to promote")
    args = ap.parse_args()

    slots_path = _abs(args.slots)
    cross_ref_path = _abs(args.cross_ref)
    out_path = _abs(args.out)
    if not slots_path.is_file():
        print(f"ERROR: missing slots file: {slots_path}")
        return 2
    if not cross_ref_path.is_file():
        print(f"ERROR: missing cross ref file: {cross_ref_path}")
        return 2

    slots = _load_jsonl(slots_path)
    cross = json.loads(cross_ref_path.read_text(encoding="utf-8"))
    entries = cross.get("entries", [])
    cross_states = {
        int(e.get("state_candidate_id"))
        for e in entries
        if isinstance(e, dict) and isinstance(e.get("state_candidate_id"), int)
    }

    only_states: set[int] = set()
    if args.state_ids.strip():
        for token in args.state_ids.split(","):
            token = token.strip()
            if token:
                only_states.add(int(token))

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    updated = 0
    out_rows: list[dict[str, Any]] = []
    for row in slots:
        out = dict(row)
        sid = out.get("state_id")
        if not isinstance(sid, int):
            out_rows.append(out)
            continue
        if only_states and sid not in only_states:
            out_rows.append(out)
            continue
        if sid not in cross_states:
            out_rows.append(out)
            continue
        ev = out.get("evidence_ref")
        if not isinstance(ev, str) or not ev.strip():
            out_rows.append(out)
            continue

        if out.get("anchor_status") != "verified":
            out["anchor_status"] = "verified"
            out["anchor_strength"] = max(float(args.strength), 0.8)
            out["updated_at_utc"] = ts
            out["verification_mode"] = "cross_ref_structural_v1"
            note = str(out.get("note", "")).strip()
            suffix = "Promoted by update_btrack_anchor_evidence.py from CROSS_REF state_candidate alignment."
            out["note"] = f"{note} {suffix}".strip()
            updated += 1
        out_rows.append(out)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for row in out_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print("OK: anchor evidence slots updated")
    print(f"updated_slots={updated}")
    print(f"out={out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
