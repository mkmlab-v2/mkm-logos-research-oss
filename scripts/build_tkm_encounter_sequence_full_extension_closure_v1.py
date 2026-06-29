#!/usr/bin/env python3
"""Build TKM encounter_sequence full extension closure rollup (P33–P48) [HYPO]."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/tkm_encounter_sequence_full_extension_closure_v1_latest.json"
ARTIFACT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_full_extension_closure_v1_latest.json"

GATE_KEYS = tuple(f"p{n}" for n in range(33, 49))
GATE_PATHS = {k: ROOT / f"docs/final/artifacts/tkm_encounter_sequence_{k}_gate_v1_latest.json" for k in GATE_KEYS}

FINAL_CLOSURE = ROOT / "reports/tkm_encounter_sequence_stack_final_closure_v1_latest.json"
EXTENSION_CLOSURE = ROOT / "reports/tkm_encounter_sequence_stack_extension_closure_v1_latest.json"
EXTENDED_BUNDLE = ROOT / "reports/tkm_encounter_sequence_extended_stack_export_bundle_v1_latest.json"
WEEKLY = ROOT / "reports/encounter_sequence_weekly_report_v1_latest.json"
OPS = ROOT / "reports/tkm_encounter_sequence_ops_closure_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _gate_status(key: str) -> dict[str, Any]:
    doc = _load(GATE_PATHS[key])
    return {
        "gate_ok": doc.get("gate_ok") is True,
        "status": doc.get(f"tkm_encounter_sequence_{key}_status"),
    }


def build() -> dict[str, Any]:
    gates = {k: _gate_status(k) for k in GATE_KEYS}
    all_gates_ok = all(g.get("gate_ok") for g in gates.values())
    final_closure = _load(FINAL_CLOSURE)
    extension_closure = _load(EXTENSION_CLOSURE)
    extended_bundle = _load(EXTENDED_BUNDLE)
    weekly = _load(WEEKLY)
    ops = _load(OPS)
    snap = extended_bundle.get("rollup_snapshot") if isinstance(extended_bundle.get("rollup_snapshot"), dict) else {}

    full_extension_closure_ok = (
        all_gates_ok
        and final_closure.get("final_closure_ok") is True
        and extension_closure.get("extension_closure_ok") is True
        and extended_bundle.get("extended_export_bundle_ok") is True
        and weekly.get("weekly_ok") is True
        and ops.get("closure_ok") is True
        and int(snap.get("curated_reviewed_count") or 0) >= 6
    )

    return {
        "schema": "tkm_encounter_sequence_full_extension_closure_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "domain_lane": "tkm_korean_han_medicine",
        "send_gate": "HOLD",
        "non_gating": True,
        "research_only": True,
        "full_extension_closure_ok": full_extension_closure_ok,
        "gates": gates,
        "gates_ok_count": sum(1 for g in gates.values() if g.get("gate_ok") is True),
        "stack_final_closure_ok": final_closure.get("final_closure_ok"),
        "stack_extension_closure_ok": extension_closure.get("extension_closure_ok"),
        "extended_export_bundle_ok": extended_bundle.get("extended_export_bundle_ok"),
        "interpret_gpu_train_attempted": snap.get("interpret_gpu_train_attempted"),
        "curated_reviewed_count": snap.get("curated_reviewed_count"),
        "curated_pending_human_review": snap.get("curated_pending_human_review"),
        "weekly_report_version": weekly.get("version"),
        "ops_closure_version": ops.get("version"),
        "ops_closure_ok": ops.get("closure_ok"),
        "stack_phases_ko": "P33–P43 core → P44 closure → P45 curated → P46 interpret → P47 extension → P48 export → P49 full extension closure",
        "note_ko": "P33–P48 full extension closure [HYPO][NON_GATING]; Track A·auto-training·진단·처방 금지.",
        "reproduce": "py scripts/build_tkm_encounter_sequence_full_extension_closure_v1.py",
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
    print(json.dumps({"ok": doc.get("full_extension_closure_ok"), "gates": doc.get("gates_ok_count")}))
    return 0 if doc.get("full_extension_closure_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
