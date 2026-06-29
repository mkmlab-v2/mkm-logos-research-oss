#!/usr/bin/env python3
"""Build TKM encounter_sequence clinical validation stub KPI (P41) [HYPO]."""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/tkm_encounter_sequence_clinical_validation_stub_v1_latest.json"
ARTIFACT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_clinical_validation_stub_v1_latest.json"
DUAL = ROOT / "reports/tkm_clinic_encounter_dual_lane_summary_v1_latest.json"
PASSIVE_INTEGRATED = ROOT / "reports/tkm_encounter_sequence_passive_integrated_rollup_v1_latest.json"
REGISTRY = ROOT / "data/clinic/encounter_sequence_curated_learning_registry_v1.jsonl"


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


def _gold_rows() -> list[dict[str, Any]]:
    ledger_mod = _load_mod("scripts/encounter_sequence_ledger_v1.py")
    logos_mod = _load_mod("scripts/tkm_encounter_sequence_logos_sidecar_v1.py")
    clf_mod = _load_mod("scripts/tkm_dummy_row_classifier_v1.py")
    records = logos_mod.latest_records_by_sequence_id(ledger_mod.iter_ledger_records(ROOT))
    return [row for row in records if not clf_mod.is_dummy_encounter_sequence(row)]


def _boundary_ok(row: dict[str, Any]) -> bool:
    if row.get("hypothesis_tier") != "B":
        return False
    if row.get("domain_lane") != "tkm_korean_han_medicine":
        return False
    bc = row.get("boundary_contract") if isinstance(row.get("boundary_contract"), dict) else {}
    return (
        bc.get("physician_final_authority") is True
        and bc.get("track_a_autobind_forbidden") is True
        and bc.get("no_emergency_autodispatch") is True
    )


def _physician_closure_ok(row: dict[str, Any]) -> bool:
    closure = row.get("physician_closure") if isinstance(row.get("physician_closure"), dict) else {}
    phys = closure.get("physician_constitution") if isinstance(closure.get("physician_constitution"), dict) else {}
    return phys.get("recorded_by_role") == "licensed_km_physician"


def _lens_stack_ok(row: dict[str, Any]) -> bool:
    return isinstance(row.get("l6_logos_ref"), dict) and isinstance(row.get("l7_conflict_resolver_ref"), dict)


def _l0_ok(row: dict[str, Any]) -> bool:
    events = row.get("l0_router_events")
    if isinstance(events, list) and len(events) >= 1:
        return True
    l0 = row.get("l0_safety_ref")
    return isinstance(l0, dict)


def _registry_review_counts() -> dict[str, int]:
    pending = reviewed = total = 0
    if not REGISTRY.is_file():
        return {"pending_human_review": 0, "reviewed": 0, "total": 0}
    for line in REGISTRY.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        total += 1
        status = str(row.get("curated_path_status") or "")
        if status == "pending_human_review":
            pending += 1
        elif status in ("ingested_to_curated", "reviewed", "human_reviewed"):
            reviewed += 1
    return {"pending_human_review": pending, "reviewed": reviewed, "total": total}


def _rate(num: int, den: int) -> float | None:
    if den <= 0:
        return None
    return round(num / den, 4)


def build() -> dict[str, Any]:
    gold = _gold_rows()
    dual = _load(DUAL)
    passive = _load(PASSIVE_INTEGRATED)
    dual_gold = dual.get("physician_gold_only") if isinstance(dual.get("physician_gold_only"), dict) else {}
    review = _registry_review_counts()

    n = len(gold)
    boundary_pass = sum(1 for r in gold if _boundary_ok(r))
    physician_pass = sum(1 for r in gold if _physician_closure_ok(r))
    lens_pass = sum(1 for r in gold if _lens_stack_ok(r))
    l0_pass = sum(1 for r in gold if _l0_ok(r))
    turn_pass = sum(
        1
        for r in gold
        if int((r.get("sequence_summary") or {}).get("turn_count") or 0) >= 1
        or len(r.get("turns") or []) >= 1
    )

    boundary_rate = _rate(boundary_pass, n)
    physician_rate = _rate(physician_pass, n)
    lens_rate = _rate(lens_pass, n)
    l0_rate = _rate(l0_pass, n)
    turn_rate = _rate(turn_pass, n)

    validation_stub_ok = (
        n >= 3
        and dual.get("dual_lane_ok") is True
        and passive.get("integrated_ok") is True
        and boundary_pass == n
        and (physician_rate or 0) >= 0.5
        and (lens_rate or 0) >= 0.75
        and (turn_rate or 0) >= 0.5
        and int(dual_gold.get("clinic_capture_count") or 0) >= 3
    )

    return {
        "schema": "tkm_encounter_sequence_clinical_validation_stub_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "domain_lane": "tkm_korean_han_medicine",
        "send_gate": "HOLD",
        "non_gating": True,
        "research_only": True,
        "validation_stub_ok": validation_stub_ok,
        "physician_gold_sequence_count": n,
        "clinic_capture_count": int(dual_gold.get("clinic_capture_count") or 0),
        "boundary_contract_pass_rate": boundary_rate,
        "physician_closure_pass_rate": physician_rate,
        "lens_stack_wired_rate": lens_rate,
        "l0_router_wired_rate": l0_rate,
        "turn_structure_pass_rate": turn_rate,
        "dual_lane_ok": dual.get("dual_lane_ok"),
        "passive_integrated_ok": passive.get("integrated_ok"),
        "curated_learning_review": review,
        "note_ko": "임상 validation stub [HYPO][NON_GATING]; Track A·진단·처방·응급 dispatch 금지.",
        "reproduce": "py scripts/build_tkm_encounter_sequence_clinical_validation_stub_v1.py",
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
    print(json.dumps({"ok": doc.get("validation_stub_ok"), "gold": doc.get("physician_gold_sequence_count")}))
    return 0 if doc.get("validation_stub_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
