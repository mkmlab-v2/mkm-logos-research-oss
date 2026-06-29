#!/usr/bin/env python3
"""Build TKM encounter_sequence 3-lens conflict resolver KPI [HYPO]."""

from __future__ import annotations

import argparse
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/tkm_encounter_sequence_conflict_resolver_kpi_v1_latest.json"


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
    resolver_mod = _load_mod("scripts/tkm_encounter_sequence_conflict_resolver_v1.py")
    ledger_mod = _load_mod("scripts/encounter_sequence_ledger_v1.py")
    logos_mod = _load_mod("scripts/tkm_encounter_sequence_logos_sidecar_v1.py")
    clf_mod = _load_mod("scripts/tkm_dummy_row_classifier_v1.py")

    records = logos_mod.latest_records_by_sequence_id(ledger_mod.iter_ledger_records(ROOT))
    gold_rows: list[dict[str, Any]] = []
    wired = 0
    status_counts: dict[str, int] = {}
    action_counts: dict[str, int] = {}
    primitive_counts: dict[str, int] = {}
    conflict_total = 0
    aligned = 0
    violations = 0

    for row in records:
        if clf_mod.is_dummy_encounter_sequence(row):
            continue
        gold_rows.append(row)
        obs = row.get("l7_conflict_resolver_ref")
        if not isinstance(obs, dict):
            continue
        wired += 1
        status = str(obs.get("resolver_status") or "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
        action = str(obs.get("final_action_observed") or "unknown")
        action_counts[action] = action_counts.get(action, 0) + 1
        prim = str(obs.get("lens_logos_top_primitive") or "unknown")
        primitive_counts[prim] = primitive_counts.get(prim, 0) + 1
        conflict_total += int(obs.get("conflict_count") or 0)
        if status == "l5_sasang_aligned":
            aligned += 1
        if resolver_mod.validate_separation(row):
            violations += 1

    gold_wired = sum(1 for r in gold_rows if isinstance(r.get("l7_conflict_resolver_ref"), dict))
    complete_candidates = sum(
        1
        for r in gold_rows
        if isinstance(r.get("l5_myeongni_ref"), dict) and isinstance(r.get("l6_logos_ref"), dict)
    )
    computed = wired
    agreement_rate = round(aligned / computed, 4) if computed else None
    gold_ok = gold_wired >= 1 and complete_candidates >= 1 and gold_wired >= complete_candidates
    kpi_ok = gold_ok and violations == 0 and computed >= 1

    return {
        "schema": "tkm_encounter_sequence_conflict_resolver_kpi_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "domain_lane": "tkm_korean_han_medicine",
        "send_gate": "HOLD",
        "non_gating": True,
        "kpi_ok": kpi_ok,
        "physician_gold_conflict_resolver_ok": gold_ok,
        "conflict_resolver_wired_count": wired,
        "physician_gold_wired_count": gold_wired,
        "physician_gold_sequence_count": len(gold_rows),
        "resolver_status_counts": status_counts,
        "final_action_observed_counts": action_counts,
        "lens_logos_top_primitive_counts": primitive_counts,
        "conflict_count_sum": conflict_total,
        "agreement_rate_l5_aligned": agreement_rate,
        "separation_violation_count": violations,
        "note_ko": "3-lens conflict resolver [HYPO][NON_GATING] — Field→Lens(3)→Conflict→Final Action 관측; Track A 합선 금지.",
        "reproduce": "py scripts/build_tkm_encounter_sequence_conflict_resolver_kpi_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc.get("kpi_ok"), "wired": doc.get("conflict_resolver_wired_count")}))
    return 0 if doc.get("kpi_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
