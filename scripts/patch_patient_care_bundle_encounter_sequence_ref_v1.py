#!/usr/bin/env python3
"""Patch patient_care_bundle provenance with encounter_sequence pointer only."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def patch_bundle(
    bundle: dict[str, Any],
    *,
    encounter_ref: str | None,
    encounter_sequence_id: str,
    encounter_sequence_ledger_ref: str | None,
) -> dict[str, Any]:
    if bundle.get("schema") != "patient_care_bundle_v1":
        raise ValueError("schema must be patient_care_bundle_v1")
    prov = dict(bundle.get("provenance") or {})
    if encounter_ref:
        prov["encounter_ref"] = encounter_ref
    prov["encounter_sequence_id"] = encounter_sequence_id
    if encounter_sequence_ledger_ref:
        prov["encounter_sequence_ledger_ref"] = encounter_sequence_ledger_ref
    prov["encounter_sequence_linked_utc"] = _utc()
    out = dict(bundle)
    out["provenance"] = prov
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bundle", type=Path, required=True)
    ap.add_argument("--encounter-sequence-id", required=True)
    ap.add_argument("--encounter-ref", default=None)
    ap.add_argument("--ledger-ref", default="data/clinic/encounter_sequence_v1.sample.jsonl")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    bundle = json.loads(args.bundle.read_text(encoding="utf-8-sig"))
    patched = patch_bundle(
        bundle,
        encounter_ref=args.encounter_ref,
        encounter_sequence_id=args.encounter_sequence_id,
        encounter_sequence_ledger_ref=args.ledger_ref,
    )
    out_path = args.out or args.bundle
    out_path.write_text(json.dumps(patched, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "encounter_sequence_id": args.encounter_sequence_id}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
