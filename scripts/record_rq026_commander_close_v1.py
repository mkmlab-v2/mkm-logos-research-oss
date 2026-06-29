#!/usr/bin/env python3
"""Record commander CLOSED for RQ-026 (human gate · B-track sim PoC archive)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
READINESS = ROOT / "docs/final/artifacts/rq026_closure_readiness_v1_latest.json"
SIGNOFF = ROOT / "docs/final/artifacts/rq026_commander_btrack_signoff_v1_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/rq026_commander_close_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p.resolve()).replace("\\", "/")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def build(*, close_reference: str, note: str = "") -> dict[str, Any]:
    readiness = _load(READINESS)
    if not readiness.get("mechanics_bundle_ok"):
        raise ValueError("mechanics_bundle_ok is false; run rq026 chain + closure readiness first")
    signoff = _load(SIGNOFF)
    if not signoff.get("approved", {}).get("rq026_btrack_continue"):
        raise ValueError("commander btrack signoff missing rq026_btrack_continue")

    ref = close_reference.strip()
    if not ref:
        raise ValueError("close_reference required")

    return {
        "schema": "rq026_commander_close_v1",
        "generated_at_utc": _utc(),
        "classification": "INTERNAL_ONLY",
        "rq_id": "RQ-026",
        "rq_026_closed": True,
        "rq_026_status": "CLOSED",
        "hypothesis_tier": "B",
        "research_only": True,
        "closed_at_utc": _utc(),
        "closed_by": "commander",
        "close_reference": ref,
        "commander_note": note.strip() or "commander close after B-track mechanics bundle + human gate",
        "evidence_pointers": {
            "closure_readiness": _rel(READINESS),
            "btrack_signoff": _rel(SIGNOFF),
            "matrix_promotion_v1_2": _rel(
                ROOT / "docs/final/artifacts/rq026_pathology_matrix_v1_2_btrack_promotion_v1_latest.json"
            ),
            "namespace": _rel(ROOT / "experiments/sasang_temperament_agents_v1"),
        },
        "explicit_not_promoted": [
            "NG-40 codec merge",
            "Track A ACTIVE report",
            "live trading",
            "MS paste KPI body",
            "CONSTITUTION body edit",
            "clinical gating via patient_care_bundle",
            "price AB / McNemar as temperament proof",
        ],
        "boundary_ack": (
            "RQ-026 CLOSED = B-track temperament sim PoC phase archived in research inbox. "
            "experiments/sasang_temperament_agents_v1/ remains [HYPO]·research_only. "
            "4 sim agents ≠ CONSTITUTION 4AI core. No Track A·NG-40·live promotion implied."
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--close-reference",
        default="COMMANDER-RQ026-CLOSE-2026-06-04",
        help="human gate reference id",
    )
    ap.add_argument("--note", default="")
    args = ap.parse_args()

    doc = build(close_reference=args.close_reference, note=args.note)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": _rel(args.out), "rq_026_status": "CLOSED"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
