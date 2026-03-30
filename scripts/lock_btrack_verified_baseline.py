#!/usr/bin/env python3
"""Lock verified-only B-Track gate outputs as baseline artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
QUALITY = ROOT / "reports" / "constitution" / "btrack_pilot" / "btrack_quality_anchor_verified_only_latest.json"
GATE = ROOT / "reports" / "constitution" / "btrack_pilot" / "btrack_promotion_gate_anchor_verified_only_latest.json"
SLOTS = ROOT / "data" / "logos" / "btrack_pilot" / "bench" / "btrack_anchor_evidence_slots_verified.jsonl"
OUT = ROOT / "reports" / "constitution" / "btrack_pilot" / "btrack_verified_baseline_lock_latest.json"


def _abs(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _jread(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Lock verified-only B-track baseline")
    ap.add_argument("--quality", default=str(QUALITY))
    ap.add_argument("--gate", default=str(GATE))
    ap.add_argument("--slots", default=str(SLOTS))
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()

    quality = _abs(args.quality)
    gate = _abs(args.gate)
    slots = _abs(args.slots)
    out = _abs(args.out)
    for p in (quality, gate, slots):
        if not p.is_file():
            print(f"ERROR: missing required file: {p}")
            return 2

    q = _jread(quality)
    g = _jread(gate)
    metrics = q.get("metrics", {})

    lock = {
        "schema": "btrack_verified_baseline_lock_v1",
        "locked_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inputs": {
            "quality_report": str(quality),
            "gate_report": str(gate),
            "verified_slots": str(slots),
        },
        "input_hashes": {
            "quality_report_sha256": _sha256(quality),
            "gate_report_sha256": _sha256(gate),
            "verified_slots_sha256": _sha256(slots),
        },
        "baseline_metrics": {
            "reproducibility_match_rate": metrics.get("reproducibility_match_rate"),
            "resolution_confidence_delta_b_minus_a": metrics.get("resolution_confidence_delta_b_minus_a"),
            "contamination_snr_delta_b_minus_a": metrics.get("contamination_snr_delta_b_minus_a"),
        },
        "baseline_decision": g.get("decision"),
        "regression_policy": {
            "require_decision": "pass",
            "reproducibility_min": 0.8,
            "resolution_min": 0.0,
            "contamination_min": 0.0,
        },
    }

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(lock, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("OK: verified baseline locked")
    print(f"out={out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
