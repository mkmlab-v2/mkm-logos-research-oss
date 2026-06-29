#!/usr/bin/env python3
"""Ingest clinic capture → clinic MVP ledger + encounter_sequence ledger [HYPO]."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/clinic_constitution_mvp_capture_disagreement_v1.example.json"
SEQ_ID = "SEQ-CLINIC-P19-01"


def _load_mod(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _clinic_ref_exists(workspace_root: Path, ref_token: str) -> bool:
    base = workspace_root / "data/clinic"
    if not base.is_dir():
        return False
    for path in sorted(base.glob("clinic_constitution_mvp_v1*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            enc = row.get("encounter") if isinstance(row.get("encounter"), dict) else {}
            if str(enc.get("ref_token") or "") == ref_token:
                return True
    return False


def ingest(
    capture: dict[str, Any],
    *,
    append_clinic_ledger: bool = True,
    sequence_id: str | None = None,
) -> dict[str, Any]:
    convert_mod = _load_mod(
        "convert_clinic_capture_to_encounter_sequence_v1",
        ROOT / "scripts/convert_clinic_capture_to_encounter_sequence_v1.py",
    )
    ledger_mod = _load_mod(
        "encounter_sequence_ledger_v1",
        ROOT / "scripts/encounter_sequence_ledger_v1.py",
    )
    seq_id = sequence_id or SEQ_ID
    clinic_appended = False
    encounter_appended = False

    if append_clinic_ledger:
        clinic_mod = _load_mod(
            "clinic_constitution_mvp_ledger_v1",
            ROOT / "scripts/clinic_constitution_mvp_ledger_v1.py",
        )
        ref_token = str((capture.get("encounter") or {}).get("ref_token") or "")
        if ref_token and _clinic_ref_exists(ROOT, ref_token):
            clinic_appended = True
        else:
            clinic_mod.append_clinic_capture_line(ROOT, capture)
            clinic_appended = True

    for row in ledger_mod.iter_ledger_records(ROOT):
        enc = row.get("encounter") if isinstance(row.get("encounter"), dict) else {}
        if str(enc.get("sequence_id") or "") == seq_id:
            return {
                "ok": True,
                "already_present": True,
                "sequence_id": seq_id,
                "clinic_appended": clinic_appended,
            }

    seq_doc = convert_mod.convert_capture(capture, sequence_id=seq_id)
    ledger_path = ledger_mod.append_encounter_sequence_line(ROOT, seq_doc)
    encounter_appended = True
    return {
        "ok": True,
        "already_present": False,
        "sequence_id": seq_id,
        "clinic_appended": clinic_appended,
        "encounter_appended": encounter_appended,
        "encounter_ledger": str(ledger_path).replace("\\", "/"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--capture-json", type=Path, default=FIXTURE)
    ap.add_argument("--skip-clinic-ledger", action="store_true")
    ap.add_argument("--sequence-id", default=SEQ_ID)
    args = ap.parse_args()
    capture = json.loads(args.capture_json.read_text(encoding="utf-8-sig"))
    doc = ingest(
        capture,
        append_clinic_ledger=not args.skip_clinic_ledger,
        sequence_id=args.sequence_id,
    )
    print(json.dumps(doc, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
