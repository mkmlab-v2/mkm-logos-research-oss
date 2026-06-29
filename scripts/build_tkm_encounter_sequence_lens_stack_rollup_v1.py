#!/usr/bin/env python3
"""Build TKM encounter_sequence full lens-stack rollup (P33–P38) [HYPO]."""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/tkm_encounter_sequence_lens_stack_rollup_v1_latest.json"
ARTIFACT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_lens_stack_rollup_v1_latest.json"

GATE_PATHS = {
    "p33": ROOT / "docs/final/artifacts/tkm_encounter_sequence_p33_gate_v1_latest.json",
    "p34": ROOT / "docs/final/artifacts/tkm_encounter_sequence_p34_gate_v1_latest.json",
    "p35": ROOT / "docs/final/artifacts/tkm_encounter_sequence_p35_gate_v1_latest.json",
    "p36": ROOT / "docs/final/artifacts/tkm_encounter_sequence_p36_gate_v1_latest.json",
    "p37": ROOT / "docs/final/artifacts/tkm_encounter_sequence_p37_gate_v1_latest.json",
    "p38": ROOT / "docs/final/artifacts/tkm_encounter_sequence_p38_gate_v1_latest.json",
}

KPI_PATHS = {
    "cross_lens": ROOT / "reports/tkm_encounter_sequence_cross_lens_kpi_v1_latest.json",
    "passive_observation": ROOT / "reports/tkm_encounter_sequence_passive_observation_v1_latest.json",
    "conflict_resolver": ROOT / "reports/tkm_encounter_sequence_conflict_resolver_kpi_v1_latest.json",
    "disagreement_cross": ROOT / "reports/tkm_encounter_sequence_disagreement_resolver_cross_kpi_v1_latest.json",
    "export_ingest": ROOT / "reports/tkm_encounter_sequence_export_ingest_kpi_v1_latest.json",
    "ops_closure": ROOT / "reports/tkm_encounter_sequence_ops_closure_v1_latest.json",
    "weekly_report": ROOT / "reports/encounter_sequence_weekly_report_v1_latest.json",
}


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


def _ledger_layer_counts() -> dict[str, int]:
    ledger_mod = _load_mod("scripts/encounter_sequence_ledger_v1.py")
    logos_mod = _load_mod("scripts/tkm_encounter_sequence_logos_sidecar_v1.py")
    clf_mod = _load_mod("scripts/tkm_dummy_row_classifier_v1.py")
    records = logos_mod.latest_records_by_sequence_id(ledger_mod.iter_ledger_records(ROOT))
    gold = 0
    l5 = l6 = l7 = 0
    for row in records:
        if clf_mod.is_dummy_encounter_sequence(row):
            continue
        gold += 1
        if isinstance(row.get("l5_myeongni_ref"), dict):
            l5 += 1
        if isinstance(row.get("l6_logos_ref"), dict):
            l6 += 1
        if isinstance(row.get("l7_conflict_resolver_ref"), dict):
            l7 += 1
    return {
        "physician_gold_sequence_count": gold,
        "l5_myeongni_wired_count": l5,
        "l6_logos_wired_count": l6,
        "l7_conflict_resolver_wired_count": l7,
    }


def build() -> dict[str, Any]:
    gates: dict[str, Any] = {}
    all_gates_ok = True
    for key, path in GATE_PATHS.items():
        doc = _load(path)
        ok = doc.get("gate_ok") is True
        all_gates_ok = all_gates_ok and ok
        status_key = f"tkm_encounter_sequence_{key}_status"
        gates[key] = {
            "gate_ok": ok,
            "status": doc.get(status_key),
            "path": str(path).replace("\\", "/"),
        }

    cross = _load(KPI_PATHS["cross_lens"])
    passive = _load(KPI_PATHS["passive_observation"])
    resolver = _load(KPI_PATHS["conflict_resolver"])
    disagreement = _load(KPI_PATHS["disagreement_cross"])
    export_ingest = _load(KPI_PATHS["export_ingest"])
    ops = _load(KPI_PATHS["ops_closure"])
    weekly = _load(KPI_PATHS["weekly_report"])
    layers = _ledger_layer_counts()

    kpi_ok = (
        cross.get("kpi_ok") is True
        and passive.get("observation_ok") is True
        and resolver.get("kpi_ok") is True
        and disagreement.get("kpi_ok") is True
        and export_ingest.get("kpi_ok") is True
        and ops.get("closure_ok") is True
    )
    rollup_ok = all_gates_ok and kpi_ok and layers.get("physician_gold_sequence_count", 0) >= 1

    return {
        "schema": "tkm_encounter_sequence_lens_stack_rollup_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "domain_lane": "tkm_korean_han_medicine",
        "send_gate": "HOLD",
        "non_gating": True,
        "rollup_ok": rollup_ok,
        "gates": gates,
        "kpi_snapshot": {
            "cross_lens_resonance_index": cross.get("cross_lens_resonance_index"),
            "motif_top1_share": cross.get("motif_top1_share"),
            "passive_observation_ok": passive.get("observation_ok"),
            "conflict_resolver_wired_count": resolver.get("conflict_resolver_wired_count"),
            "agreement_rate_l5_aligned": resolver.get("agreement_rate_l5_aligned"),
            "disagreement_count": disagreement.get("disagreement_count"),
            "disagreement_resolver_wired_count": disagreement.get("disagreement_resolver_wired_count"),
            "disagreement_physician_authority_rate": disagreement.get("disagreement_physician_authority_rate"),
            "export_ingest_live_ok": export_ingest.get("live_ingest_ok"),
            "ops_closure_version": ops.get("version"),
            "full_stack_closure_ok": ops.get("full_stack_closure_ok"),
            "weekly_report_version": weekly.get("version"),
        },
        "ledger_layer_counts": layers,
        "lens_order_ko": "Field(L4 사상) → L5 명리 → L6 성경 → L7 cross-lens → conflict resolver → disagreement×resolver",
        "note_ko": "전체 lens stack rollup [HYPO][NON_GATING]; NotebookLM/ops 참고용; Track A 합선 금지.",
        "reproduce": "py scripts/build_tkm_encounter_sequence_lens_stack_rollup_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--mirror-artifact", action="store_true", default=True)
    ap.add_argument("--no-mirror-artifact", action="store_false", dest="mirror_artifact")
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.mirror_artifact:
        ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(args.out, ARTIFACT)
    print(json.dumps({"ok": doc.get("rollup_ok"), "gates": len(doc.get("gates") or {})}))
    return 0 if doc.get("rollup_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
