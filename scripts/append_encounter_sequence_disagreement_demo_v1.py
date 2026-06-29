#!/usr/bin/env python3
"""Idempotent append of disagreement demo row to encounter_sequence ledger [HYPO]."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/encounter_sequence_disagreement_v1.example.json"
SEQ_ID = "SEQ-DISAGREE-01"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    args = ap.parse_args()
    import importlib.util

    ledger_path = ROOT / "scripts" / "encounter_sequence_ledger_v1.py"
    spec = importlib.util.spec_from_file_location("encounter_sequence_ledger_v1", ledger_path)
    if spec is None or spec.loader is None:
        raise SystemExit(1)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    for row in mod.iter_ledger_records(ROOT):
        enc = row.get("encounter") if isinstance(row.get("encounter"), dict) else {}
        if str(enc.get("sequence_id") or "") == SEQ_ID:
            print(json.dumps({"ok": True, "applied": False, "already_present": True}))
            return 0

    doc = json.loads(FIXTURE.read_text(encoding="utf-8-sig"))
    out = mod.append_encounter_sequence_line(ROOT, doc)
    print(json.dumps({"ok": True, "applied": True, "ledger": str(out)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
