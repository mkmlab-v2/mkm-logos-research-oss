#!/usr/bin/env python3
"""Backfill physician_gold disagreement rows with L5/L6/L7 sidecars [HYPO]."""

from __future__ import annotations

import argparse
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/tkm_disagreement_lens_stack_backfill_v1_latest.json"


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


def run(*, dry_run: bool = False) -> dict[str, Any]:
    ledger_mod = _load_mod("scripts/encounter_sequence_ledger_v1.py")
    logos_mod = _load_mod("scripts/tkm_encounter_sequence_logos_sidecar_v1.py")
    myeongni_mod = _load_mod("scripts/tkm_encounter_sequence_myeongni_sidecar_v1.py")
    resolver_mod = _load_mod("scripts/tkm_encounter_sequence_conflict_resolver_v1.py")
    clf_mod = _load_mod("scripts/tkm_dummy_row_classifier_v1.py")

    records = logos_mod.latest_records_by_sequence_id(ledger_mod.iter_ledger_records(ROOT))
    patched = 0
    skipped = 0
    disagreement_targets = 0
    appended: list[str] = []

    for row in records:
        if clf_mod.is_dummy_encounter_sequence(row):
            skipped += 1
            continue
        physician = row.get("physician_closure") if isinstance(row.get("physician_closure"), dict) else {}
        agr = physician.get("agreement") if isinstance(physician.get("agreement"), dict) else {}
        if agr.get("ai_physician_match") is not False:
            continue
        disagreement_targets += 1
        enc = row.get("encounter") if isinstance(row.get("encounter"), dict) else {}
        seq_id = str(enc.get("sequence_id") or "")
        if not seq_id:
            continue

        new_row = dict(row)
        changed = False
        if not isinstance(new_row.get("l5_myeongni_ref"), dict) and myeongni_mod.birth_profile_present(new_row):
            myeongni_mod.ensure_stub_report()
            new_row = myeongni_mod.attach_sidecar(new_row)
            changed = True
        if not isinstance(new_row.get("l6_logos_ref"), dict):
            new_row = logos_mod.attach_sidecar(new_row)
            changed = True
        if isinstance(new_row.get("l6_logos_ref"), dict) and not isinstance(new_row.get("l7_conflict_resolver_ref"), dict):
            new_row = resolver_mod.attach_observation(new_row)
            changed = True

        if not changed:
            skipped += 1
            continue
        sep_errs = (
            myeongni_mod.validate_sasang_lens_separation(new_row)
            + logos_mod.validate_logos_lens_separation(new_row)
            + resolver_mod.validate_separation(new_row)
        )
        if sep_errs:
            return {"ok": False, "reason": "separation_failed", "errors": sep_errs, "sequence_id": seq_id}

        if dry_run:
            patched += 1
            appended.append(seq_id)
            continue
        ledger_mod.append_encounter_sequence_line(ROOT, new_row, set_generated_at_if_missing=False)
        patched += 1
        appended.append(seq_id)

    return {
        "schema": "tkm_disagreement_lens_stack_backfill_v1",
        "generated_at_utc": _utc(),
        "ok": disagreement_targets >= 1,
        "dry_run": dry_run,
        "disagreement_target_count": disagreement_targets,
        "patched_count": patched,
        "skipped_count": skipped,
        "sequence_ids": appended,
        "send_gate": "HOLD",
        "reproduce": "py scripts/backfill_tkm_disagreement_lens_stack_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = run(dry_run=args.dry_run)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc.get("ok"), "patched": doc.get("patched_count"), "targets": doc.get("disagreement_target_count")}))
    return 0 if doc.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
