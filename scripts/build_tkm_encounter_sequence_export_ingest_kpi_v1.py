#!/usr/bin/env python3
"""Build TKM export/ingest live lens-stack KPI [HYPO]."""

from __future__ import annotations

import argparse
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/tkm_encounter_sequence_export_ingest_kpi_v1_latest.json"
INGEST = ROOT / "reports/tkm_physician_gold_capture_export_ingest_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _load_mod(rel: str):
    path = ROOT / rel
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _row_by_sequence_id(seq_id: str) -> dict[str, Any] | None:
    ledger_mod = _load_mod("scripts/encounter_sequence_ledger_v1.py")
    logos_mod = _load_mod("scripts/tkm_encounter_sequence_logos_sidecar_v1.py")
    records = logos_mod.latest_records_by_sequence_id(ledger_mod.iter_ledger_records(ROOT))
    for row in records:
        enc = row.get("encounter") if isinstance(row.get("encounter"), dict) else {}
        if str(enc.get("sequence_id") or "") == seq_id:
            return row
    return None


def build() -> dict[str, Any]:
    ingest = _load(INGEST)
    seq_id = str(ingest.get("sequence_id") or "")
    row = _row_by_sequence_id(seq_id) if seq_id else None
    has_l5 = isinstance((row or {}).get("l5_myeongni_ref"), dict)
    has_l6 = isinstance((row or {}).get("l6_logos_ref"), dict)
    has_l7 = isinstance((row or {}).get("l7_conflict_resolver_ref"), dict)
    live_ingest_ok = ingest.get("ok") is True and ingest.get("export_only") is not True
    lens_stack_ok = live_ingest_ok and has_l6 and has_l7
    kpi_ok = live_ingest_ok and lens_stack_ok and bool(seq_id)
    return {
        "schema": "tkm_encounter_sequence_export_ingest_kpi_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "send_gate": "HOLD",
        "non_gating": True,
        "kpi_ok": kpi_ok,
        "live_ingest_ok": live_ingest_ok,
        "lens_stack_ok": lens_stack_ok,
        "sequence_id": seq_id or None,
        "has_l5_myeongni_ref": has_l5,
        "has_l6_logos_ref": has_l6,
        "has_l7_conflict_resolver_ref": has_l7,
        "export_path": ingest.get("export_path"),
        "note_ko": "Export/ingest live [HYPO] — clinic capture→ledger 시 L6/L7 자동 attach 검증.",
        "reproduce": "py scripts/build_tkm_encounter_sequence_export_ingest_kpi_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc.get("kpi_ok"), "sequence_id": doc.get("sequence_id")}))
    return 0 if doc.get("kpi_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
