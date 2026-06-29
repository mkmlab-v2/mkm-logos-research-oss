#!/usr/bin/env python3
"""Backfill encounter_sequence ledger with l7_conflict_resolver_ref [HYPO]."""

from __future__ import annotations

import argparse
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/tkm_encounter_sequence_conflict_resolver_apply_v1_latest.json"


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


def run(*, dry_run: bool = False, force: bool = False) -> dict[str, Any]:
    resolver_mod = _load_mod("scripts/tkm_encounter_sequence_conflict_resolver_v1.py")
    ledger_mod = _load_mod("scripts/encounter_sequence_ledger_v1.py")
    logos_mod = _load_mod("scripts/tkm_encounter_sequence_logos_sidecar_v1.py")
    clf_mod = _load_mod("scripts/tkm_dummy_row_classifier_v1.py")

    records = logos_mod.latest_records_by_sequence_id(ledger_mod.iter_ledger_records(ROOT))
    patched = 0
    skipped = 0
    existing = 0
    appended: list[str] = []

    for row in records:
        if clf_mod.is_dummy_encounter_sequence(row):
            skipped += 1
            continue
        enc = row.get("encounter") if isinstance(row.get("encounter"), dict) else {}
        seq_id = str(enc.get("sequence_id") or "")
        if not seq_id:
            continue
        if isinstance(row.get("l7_conflict_resolver_ref"), dict) and not force:
            existing += 1
            skipped += 1
            continue
        new_row = resolver_mod.attach_observation(row, force=force)
        sep_errs = resolver_mod.validate_separation(new_row)
        if sep_errs:
            return {"ok": False, "reason": "separation_failed", "errors": sep_errs, "sequence_id": seq_id}
        if not isinstance(new_row.get("l7_conflict_resolver_ref"), dict):
            skipped += 1
            continue
        if dry_run:
            patched += 1
            appended.append(seq_id)
            continue
        ledger_mod.append_encounter_sequence_line(ROOT, new_row, set_generated_at_if_missing=False)
        patched += 1
        appended.append(seq_id)

    return {
        "schema": "tkm_encounter_sequence_conflict_resolver_apply_v1",
        "generated_at_utc": _utc(),
        "ok": patched >= 1 or existing >= 1,
        "dry_run": dry_run,
        "force": force,
        "patched_count": patched,
        "existing_sidecar_count": existing,
        "skipped_count": skipped,
        "sequence_ids": appended,
        "send_gate": "HOLD",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = run(dry_run=args.dry_run, force=args.force)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc.get("ok"), "patched": doc.get("patched_count"), "existing": doc.get("existing_sidecar_count")}))
    return 0 if doc.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
