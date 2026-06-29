#!/usr/bin/env python3
"""Build TKM encounter_sequence L5 myeongni KPI rollup [HYPO]."""

from __future__ import annotations

import argparse
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/tkm_encounter_sequence_myeongni_kpi_v1_latest.json"


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
    sidecar_mod = _load_mod("scripts/tkm_encounter_sequence_myeongni_sidecar_v1.py")
    clf_mod = _load_mod("scripts/tkm_dummy_row_classifier_v1.py")

    records = sidecar_mod.latest_records_by_sequence_id(ledger_mod.iter_ledger_records(ROOT))
    gold_rows: list[dict[str, Any]] = []
    all_with_birth = 0
    all_with_sidecar = 0
    linked = 0
    engine_linked = 0
    stub_linked = 0
    cross_counts: dict[str, int] = {}
    computed_cross = 0

    for row in records:
        enc = row.get("encounter") if isinstance(row.get("encounter"), dict) else {}
        seq_id = str(enc.get("sequence_id") or "")
        if not seq_id:
            continue
        if sidecar_mod.birth_profile_present(row):
            all_with_birth += 1
        sidecar = row.get("l5_myeongni_ref")
        if isinstance(sidecar, dict):
            all_with_sidecar += 1
            ref = str(sidecar.get("myeongni_report_ref") or "")
            if ref and (ROOT / ref).is_file():
                linked += 1
                if sidecar_mod._is_engine_report(ref):
                    engine_linked += 1
                elif "stub" in ref:
                    stub_linked += 1
            status = str(sidecar.get("cross_check_status") or "not_computed")
            cross_counts[status] = cross_counts.get(status, 0) + 1
            if status != "not_computed":
                computed_cross += 1
        if not clf_mod.is_dummy_encounter_sequence(row):
            gold_rows.append(row)

    gold_birth = sum(1 for r in gold_rows if sidecar_mod.birth_profile_present(r))
    gold_sidecar = sum(1 for r in gold_rows if isinstance(r.get("l5_myeongni_ref"), dict))
    gold_linked = 0
    gold_engine_linked = 0
    gold_stub_linked = 0
    for r in gold_rows:
        sc = r.get("l5_myeongni_ref")
        if isinstance(sc, dict):
            ref = str(sc.get("myeongni_report_ref") or "")
            if ref and (ROOT / ref).is_file():
                gold_linked += 1
                if sidecar_mod._is_engine_report(ref):
                    gold_engine_linked += 1
                elif "stub" in ref:
                    gold_stub_linked += 1

    def _rate(num: int, den: int) -> float | None:
        if not den:
            return None
        return round(num / den, 4)

    kpi_ok = (
        all_with_birth >= 1
        and all_with_sidecar >= 1
        and linked >= 1
        and computed_cross >= 1
        and engine_linked >= 1
    )
    gold_engine_ok = gold_sidecar >= 1 and gold_stub_linked == 0 and gold_engine_linked == gold_sidecar
    return {
        "schema": "tkm_encounter_sequence_myeongni_kpi_v1",
        "version": "1.2.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "send_gate": "HOLD",
        "kpi_ok": kpi_ok,
        "physician_gold_engine_ok": gold_engine_ok,
        "all_ledger": {
            "sequence_count": len(records),
            "birth_profile_present_count": all_with_birth,
            "myeongni_sidecar_count": all_with_sidecar,
            "myeongni_report_linked_count": linked,
            "engine_report_linked_count": engine_linked,
            "stub_report_linked_count": stub_linked,
            "engine_report_linked_rate": _rate(engine_linked, all_with_sidecar) if all_with_sidecar else None,
            "birth_profile_present_rate": _rate(all_with_birth, len(records)),
            "myeongni_report_linked_rate": _rate(linked, all_with_birth) if all_with_birth else None,
            "cross_check_status_counts": cross_counts,
            "cross_check_computed_count": computed_cross,
            "cross_check_computed_rate": _rate(computed_cross, all_with_sidecar) if all_with_sidecar else None,
        },
        "physician_gold_only": {
            "sequence_count": len(gold_rows),
            "birth_profile_present_count": gold_birth,
            "myeongni_sidecar_count": gold_sidecar,
            "myeongni_report_linked_count": gold_linked,
            "engine_report_linked_count": gold_engine_linked,
            "stub_report_linked_count": gold_stub_linked,
            "engine_report_linked_rate": _rate(gold_engine_linked, gold_sidecar) if gold_sidecar else None,
            "birth_profile_present_rate": _rate(gold_birth, len(gold_rows)) if gold_rows else None,
            "myeongni_report_linked_rate": _rate(gold_linked, gold_birth) if gold_birth else None,
        },
        "note_ko": "L5 명리 KPI는 [HYPO]·non_gating; 헤드라인 사상 match_rate와 합선 금지.",
        "reproduce": "py scripts/build_tkm_encounter_sequence_myeongni_kpi_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": doc.get("kpi_ok"),
                "linked_rate": (doc.get("all_ledger") or {}).get("myeongni_report_linked_rate"),
            }
        )
    )
    return 0 if doc.get("kpi_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
