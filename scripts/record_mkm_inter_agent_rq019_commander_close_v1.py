#!/usr/bin/env python3
"""Record commander close of RQ-019 after counsel sign-off (human gate)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SIGNOFF = ROOT / "docs/final/artifacts/mkm_inter_agent_legal_counsel_signoff_v1_latest.json"
READINESS = ROOT / "docs/final/artifacts/mkm_inter_agent_rq019_closure_readiness_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/mkm_inter_agent_rq019_commander_close_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _path_ref(path: Path) -> str:
    return path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else path.as_posix()


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"missing required artifact: {path}")
    doc = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise ValueError(f"invalid JSON object: {path}")
    return doc


def build(*, counsel_reference: str, note: str = "") -> dict[str, Any]:
    signoff = _load(SIGNOFF)
    if not signoff.get("counsel_signoff"):
        raise ValueError("counsel sign-off required before commander close")
    ref = counsel_reference.strip()
    if not ref:
        raise ValueError("counsel_reference required")
    signoff_ref = str(signoff.get("counsel_reference") or "").strip()
    if signoff_ref and signoff_ref != ref:
        raise ValueError(f"counsel_reference mismatch: signoff={signoff_ref!r} arg={ref!r}")

    readiness: dict[str, Any] | None = None
    if READINESS.is_file():
        readiness = json.loads(READINESS.read_text(encoding="utf-8"))
        if isinstance(readiness, dict) and not readiness.get("closure_allowed"):
            raise ValueError("closure_readiness.closure_allowed is false; rebuild readiness first")

    return {
        "schema": "mkm_inter_agent_rq019_commander_close_v1",
        "generated_at_utc": _utc_now(),
        "classification": "INTERNAL_ONLY",
        "rq_019_closed": True,
        "rq_019_status": "CLOSED",
        "closed_at_utc": _utc_now(),
        "counsel_reference": ref,
        "counsel_signoff_pointer": _path_ref(SIGNOFF),
        "closure_readiness_pointer": _path_ref(READINESS) if READINESS.is_file() else None,
        "commander_note": note.strip() or None,
        "boundary_ack": (
            "RQ-019 closed for inter-agent encoding milestone pack. "
            "External send still requires PUBLIC_FACING v1.7 per message. "
            "No Track A bench or live-trading promotion implied."
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--counsel-reference", required=True)
    ap.add_argument("--note", default="commander verbal close after LC clearance")
    args = ap.parse_args()
    doc = build(counsel_reference=args.counsel_reference, note=args.note)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"ok": True, "output": str(args.out_json), "rq_019_status": doc["rq_019_status"]},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
