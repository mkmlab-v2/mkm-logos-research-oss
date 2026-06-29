#!/usr/bin/env python3
"""Backfill engine myeongni reports for ledger rows still on stub [HYPO]."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
OUT = ROOT / "reports/tkm_myeongni_engine_ledger_backfill_v1_latest.json"
DEFAULT_STUB = "reports/myeongni_physician_gold_stub_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_mod(rel: str):
    path = ROOT / rel
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _row_to_capture(record: dict[str, Any]) -> dict[str, Any]:
    enc = record.get("encounter") if isinstance(record.get("encounter"), dict) else {}
    return {
        "schema": "clinic_constitution_mvp_capture_v1",
        "encounter": enc,
        "modalities_present": {"birth_profile": True},
    }


def run(*, include_dummy: bool = False, dry_run: bool = False) -> dict[str, Any]:
    ledger_mod = _load_mod("scripts/encounter_sequence_ledger_v1.py")
    sidecar_mod = _load_mod("scripts/tkm_encounter_sequence_myeongni_sidecar_v1.py")
    clf_mod = _load_mod("scripts/tkm_dummy_row_classifier_v1.py")
    builder = _load_mod("scripts/build_physician_gold_myeongni_engine_report_v1.py")
    birth_mod = _load_mod("scripts/tkm_physician_gold_birth_profile_v1.py")

    records = sidecar_mod.latest_records_by_sequence_id(ledger_mod.iter_ledger_records(ROOT))
    targets: dict[str, dict[str, Any]] = {}
    for row in records:
        if not sidecar_mod.birth_profile_present(row):
            continue
        if not include_dummy and clf_mod.is_dummy_encounter_sequence(row):
            continue
        sc = row.get("l5_myeongni_ref")
        if not isinstance(sc, dict):
            continue
        ref_rel = str(sc.get("myeongni_report_ref") or "")
        if sidecar_mod._is_engine_report(ref_rel):
            continue
        if DEFAULT_STUB not in ref_rel and ref_rel:
            continue
        token = str((row.get("encounter") or {}).get("ref_token") or "")
        if not token:
            continue
        mapped = sidecar_mod.REF_TOKEN_MYEONGNI_MAP.get(token)
        if mapped and (ROOT / mapped).is_file():
            continue
        targets[token] = row

    built = 0
    skipped = 0
    built_refs: list[str] = []
    for token, row in sorted(targets.items()):
        rel = birth_mod.engine_report_relpath(token)
        if (ROOT / rel).is_file():
            skipped += 1
            continue
        if dry_run:
            built += 1
            built_refs.append(token)
            continue
        doc = builder.build_for_capture(_row_to_capture(row))
        if doc.get("ok"):
            built += 1
            built_refs.append(token)

    return {
        "schema": "tkm_myeongni_engine_ledger_backfill_v1",
        "generated_at_utc": _utc(),
        "ok": len(targets) == 0 or built >= 1 or skipped >= 1,
        "dry_run": dry_run,
        "include_dummy": include_dummy,
        "target_count": len(targets),
        "built_count": built,
        "skipped_existing_count": skipped,
        "ref_tokens": built_refs,
        "send_gate": "HOLD",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--include-dummy", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = run(include_dummy=args.include_dummy, dry_run=args.dry_run)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc.get("ok"), "built": doc.get("built_count"), "targets": doc.get("target_count")}))
    return 0 if doc.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
