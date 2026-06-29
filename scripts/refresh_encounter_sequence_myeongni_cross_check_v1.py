#!/usr/bin/env python3
"""Recompute l5_myeongni_ref.cross_check_status on encounter_sequence ledger [HYPO]."""

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
OUT = ROOT / "reports/tkm_encounter_sequence_myeongni_cross_refresh_v1_latest.json"


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
    sidecar_mod = _load_mod("scripts/tkm_encounter_sequence_myeongni_sidecar_v1.py")
    ledger_mod = _load_mod("scripts/encounter_sequence_ledger_v1.py")
    sidecar_mod.ensure_stub_report()

    records = sidecar_mod.latest_records_by_sequence_id(ledger_mod.iter_ledger_records(ROOT))
    refreshed = 0
    skipped = 0
    status_counts: dict[str, int] = {}
    sequence_ids: list[str] = []

    for row in records:
        enc = row.get("encounter") if isinstance(row.get("encounter"), dict) else {}
        seq_id = str(enc.get("sequence_id") or "")
        if not seq_id:
            continue
        if not isinstance(row.get("l5_myeongni_ref"), dict):
            skipped += 1
            continue
        new_row = sidecar_mod.attach_sidecar(row, force=True)
        sep_errs = sidecar_mod.validate_sasang_lens_separation(new_row)
        if sep_errs:
            return {"ok": False, "reason": "separation_failed", "errors": sep_errs, "sequence_id": seq_id}
        sidecar = new_row.get("l5_myeongni_ref")
        status = str((sidecar or {}).get("cross_check_status") or "not_computed")
        status_counts[status] = status_counts.get(status, 0) + 1
        if dry_run:
            refreshed += 1
            sequence_ids.append(seq_id)
            continue
        ledger_mod.append_encounter_sequence_line(ROOT, new_row, set_generated_at_if_missing=False)
        refreshed += 1
        sequence_ids.append(seq_id)

    computed = sum(v for k, v in status_counts.items() if k != "not_computed")
    return {
        "schema": "tkm_encounter_sequence_myeongni_cross_refresh_v1",
        "generated_at_utc": _utc(),
        "ok": refreshed >= 1 and computed >= 1,
        "dry_run": dry_run,
        "refreshed_count": refreshed,
        "skipped_count": skipped,
        "cross_check_status_counts": status_counts,
        "cross_check_computed_count": computed,
        "sequence_ids": sequence_ids,
        "send_gate": "HOLD",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = run(dry_run=args.dry_run)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": doc.get("ok"),
                "refreshed": doc.get("refreshed_count"),
                "computed": doc.get("cross_check_computed_count"),
            }
        )
    )
    return 0 if doc.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
