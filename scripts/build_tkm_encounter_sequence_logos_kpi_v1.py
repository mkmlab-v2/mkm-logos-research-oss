#!/usr/bin/env python3
"""Build TKM encounter_sequence L6 logos cosmic anchor KPI rollup [HYPO]."""

from __future__ import annotations

import argparse
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/tkm_encounter_sequence_logos_kpi_v1_latest.json"


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


def build() -> dict[str, Any]:
    ledger_mod = _load_mod("scripts/encounter_sequence_ledger_v1.py")
    logos_mod = _load_mod("scripts/tkm_encounter_sequence_logos_sidecar_v1.py")
    clf_mod = _load_mod("scripts/tkm_dummy_row_classifier_v1.py")

    records = logos_mod.latest_records_by_sequence_id(ledger_mod.iter_ledger_records(ROOT))
    gold_rows: list[dict[str, Any]] = []
    all_with_sidecar = 0
    linked = 0
    non_gating_ok = 0
    motif_counts: dict[str, int] = {}

    for row in records:
        sidecar = row.get("l6_logos_ref")
        if isinstance(sidecar, dict):
            all_with_sidecar += 1
            ref = str(sidecar.get("logos_cosmic_anchor_ref") or "")
            if ref and (ROOT / ref).is_file():
                linked += 1
            if sidecar.get("non_gating") is True:
                non_gating_ok += 1
            stem = str(sidecar.get("motif_file_stem") or "unknown")
            motif_counts[stem] = motif_counts.get(stem, 0) + 1
        if not clf_mod.is_dummy_encounter_sequence(row):
            gold_rows.append(row)

    gold_sidecar = sum(1 for r in gold_rows if isinstance(r.get("l6_logos_ref"), dict))
    gold_linked = 0
    for r in gold_rows:
        sc = r.get("l6_logos_ref")
        if isinstance(sc, dict):
            ref = str(sc.get("logos_cosmic_anchor_ref") or "")
            if ref and (ROOT / ref).is_file():
                gold_linked += 1

    def _rate(num: int, den: int) -> float | None:
        if not den:
            return None
        return round(num / den, 4)

    kpi_ok = all_with_sidecar >= 1 and linked >= 1 and non_gating_ok == all_with_sidecar
    gold_ok = gold_sidecar >= 1 and gold_linked == gold_sidecar
    return {
        "schema": "tkm_encounter_sequence_logos_kpi_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "send_gate": "HOLD",
        "kpi_ok": kpi_ok,
        "physician_gold_logos_ok": gold_ok,
        "all_ledger": {
            "sequence_count": len(records),
            "logos_sidecar_count": all_with_sidecar,
            "logos_anchor_linked_count": linked,
            "logos_anchor_linked_rate": _rate(linked, all_with_sidecar) if all_with_sidecar else None,
            "non_gating_count": non_gating_ok,
            "motif_file_stem_counts": motif_counts,
        },
        "physician_gold_only": {
            "sequence_count": len(gold_rows),
            "logos_sidecar_count": gold_sidecar,
            "logos_anchor_linked_count": gold_linked,
            "logos_anchor_linked_rate": _rate(gold_linked, gold_sidecar) if gold_sidecar else None,
        },
        "note_ko": "L6 Logos [HYPO][NON_GATING]; 성경 cosmic anchor만. 사상·명리 헤드라인 합선 금지.",
        "reproduce": "py scripts/build_tkm_encounter_sequence_logos_kpi_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc.get("kpi_ok"), "gold_ok": doc.get("physician_gold_logos_ok")}))
    return 0 if doc.get("kpi_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
