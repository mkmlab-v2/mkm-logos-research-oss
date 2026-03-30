#!/usr/bin/env python3
"""Verify anchor evidence slots and emit verified-only subset."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SLOTS = ROOT / "data" / "logos" / "btrack_pilot" / "bench" / "btrack_anchor_evidence_slots.jsonl"
VERIFIED_OUT = ROOT / "data" / "logos" / "btrack_pilot" / "bench" / "btrack_anchor_evidence_slots_verified.jsonl"
REPORT_OUT = ROOT / "reports" / "constitution" / "btrack_pilot" / "btrack_anchor_evidence_verification_latest.json"


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


def _is_verified_slot(row: dict[str, Any]) -> tuple[bool, list[str]]:
    errs: list[str] = []
    if row.get("anchor_status") != "verified":
        errs.append("anchor_status must be 'verified'")
    ev = row.get("evidence_ref")
    if not isinstance(ev, str) or not ev.strip():
        errs.append("evidence_ref is required")
    strength = row.get("anchor_strength")
    if not isinstance(strength, (int, float)) or float(strength) < 0.8:
        errs.append("anchor_strength must be >= 0.8 for verified slots")
    for k in ("confidence_boost", "snr_boost"):
        v = row.get(k)
        if not isinstance(v, (int, float)):
            errs.append(f"{k} must be numeric")
    return (len(errs) == 0, errs)


def main() -> int:
    ap = argparse.ArgumentParser(description="Verify anchor evidence slots")
    ap.add_argument("--slots", default=str(SLOTS))
    ap.add_argument("--verified-out", default=str(VERIFIED_OUT))
    ap.add_argument("--report-out", default=str(REPORT_OUT))
    args = ap.parse_args()

    slots_path = _abs(args.slots)
    verified_out = _abs(args.verified_out)
    report_out = _abs(args.report_out)
    if not slots_path.is_file():
        print(f"ERROR: missing slots file: {slots_path}")
        return 2

    rows = _load_jsonl(slots_path)
    verified: list[dict[str, Any]] = []
    pending: list[dict[str, Any]] = []
    for r in rows:
        ok, errs = _is_verified_slot(r)
        if ok:
            verified.append(r)
        else:
            pending.append(
                {
                    "key": r.get("key"),
                    "state_id": r.get("state_id"),
                    "anchor_status": r.get("anchor_status"),
                    "errors": errs,
                }
            )

    verified_out.parent.mkdir(parents=True, exist_ok=True)
    with verified_out.open("w", encoding="utf-8") as f:
        for row in verified:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    report = {
        "schema": "btrack_anchor_evidence_verification_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "input_slots": str(slots_path),
        "verified_out": str(verified_out),
        "counts": {
            "total_slots": len(rows),
            "verified_slots": len(verified),
            "pending_slots": len(pending),
        },
        "pending": pending,
        "pass": len(pending) == 0,
    }
    report_out.parent.mkdir(parents=True, exist_ok=True)
    report_out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("OK: anchor evidence verification complete")
    print(f"verified_slots={len(verified)} pending_slots={len(pending)}")
    print(f"report={report_out}")
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
