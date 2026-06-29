#!/usr/bin/env python3
"""Ingest physician_gold clinic capture (non-dummy) → ledgers [HYPO]."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/clinic_constitution_mvp_capture_physician_gold_v1.example.json"
SEQ_ID = "SEQ-PHYSICIAN-GOLD-P21-01"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--capture-json", type=Path, default=FIXTURE)
    ap.add_argument("--sequence-id", default=SEQ_ID)
    args = ap.parse_args()

    import importlib.util

    class_path = ROOT / "scripts/tkm_dummy_row_classifier_v1.py"
    spec_c = importlib.util.spec_from_file_location("tkm_dummy_row_classifier_v1", class_path)
    if spec_c is None or spec_c.loader is None:
        raise SystemExit(1)
    clf = importlib.util.module_from_spec(spec_c)
    spec_c.loader.exec_module(clf)

    capture = json.loads(args.capture_json.read_text(encoding="utf-8-sig"))
    if clf.is_dummy_clinic_capture(capture):
        print(json.dumps({"ok": False, "reason": "dummy_capture_rejected"}))
        return 2

    ingest_path = ROOT / "scripts/ingest_clinic_capture_to_encounter_sequence_v1.py"
    spec = importlib.util.spec_from_file_location("ingest_clinic_capture_to_encounter_sequence_v1", ingest_path)
    if spec is None or spec.loader is None:
        raise SystemExit(1)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    doc = mod.ingest(capture, append_clinic_ledger=True, sequence_id=args.sequence_id)
    print(json.dumps({"ok": True, "physician_gold": True, **doc}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
