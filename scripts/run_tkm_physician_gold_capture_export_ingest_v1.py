#!/usr/bin/env python3
"""Export physician_gold capture template + optional ingest [HYPO]."""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "tests/fixtures/clinic_constitution_mvp_capture_physician_gold_v1.example.json"
INBOX = ROOT / "data/clinic/inbox"
OUT = ROOT / "reports/tkm_physician_gold_capture_export_ingest_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_mod(name: str, rel: str):
    path = ROOT / rel
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run(*, capture_json: Path | None = None, sequence_id: str | None = None, export_only: bool = False) -> dict[str, Any]:
    INBOX.mkdir(parents=True, exist_ok=True)
    export_path = INBOX / "physician_gold_capture_template_latest.json"
    src = capture_json if capture_json and capture_json.is_file() else TEMPLATE
    doc = json.loads(src.read_text(encoding="utf-8-sig"))
    doc["meta"] = {**(doc.get("meta") if isinstance(doc.get("meta"), dict) else {}), "export_template": True}
    export_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if export_only:
        return {
            "schema": "tkm_physician_gold_capture_export_ingest_v1",
            "generated_at_utc": _utc(),
            "ok": True,
            "export_only": True,
            "export_path": str(export_path).replace("\\", "/"),
        }

    clf = _load_mod("tkm_dummy_row_classifier_v1", "scripts/tkm_dummy_row_classifier_v1.py")
    if clf.is_dummy_clinic_capture(doc):
        return {"ok": False, "reason": "dummy_capture_rejected", "export_path": str(export_path)}

    ref = str((doc.get("encounter") or {}).get("ref_token") or "ENC-EXPORT-UNKNOWN")
    seq = sequence_id or f"SEQ-{ref.replace('ENC-', '')[:48]}"
    ingest_mod = _load_mod(
        "ingest_clinic_capture_to_encounter_sequence_v1",
        "scripts/ingest_clinic_capture_to_encounter_sequence_v1.py",
    )
    ingest_doc = ingest_mod.ingest(doc, append_clinic_ledger=True, sequence_id=seq)
    return {
        "schema": "tkm_physician_gold_capture_export_ingest_v1",
        "generated_at_utc": _utc(),
        "ok": True,
        "export_path": str(export_path).replace("\\", "/"),
        "sequence_id": seq,
        "ingest": ingest_doc,
        "send_gate": "HOLD",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--capture-json", type=Path, default=None)
    ap.add_argument("--sequence-id", default=None)
    ap.add_argument("--export-only", action="store_true")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = run(capture_json=args.capture_json, sequence_id=args.sequence_id, export_only=args.export_only)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc.get("ok"), "export_path": doc.get("export_path")}))
    return 0 if doc.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
