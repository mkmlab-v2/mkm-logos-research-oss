#!/usr/bin/env python3
"""Build TKM encounter_sequence integrated stack closure rollup (P33–P50) [HYPO]."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/tkm_encounter_sequence_integrated_stack_closure_v1_latest.json"
ARTIFACT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_integrated_stack_closure_v1_latest.json"

GATE_KEYS = tuple(f"p{n}" for n in range(33, 51))
GATE_PATHS = {k: ROOT / f"docs/final/artifacts/tkm_encounter_sequence_{k}_gate_v1_latest.json" for k in GATE_KEYS}

FULL_EXTENSION = ROOT / "reports/tkm_encounter_sequence_full_extension_closure_v1_latest.json"
POST_EXTENSION = ROOT / "reports/tkm_encounter_sequence_post_extension_observation_v1_latest.json"
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
    full_ext = _load(FULL_EXTENSION)
    post_ext = _load(POST_EXTENSION)
    extended_bundle = _load(EXTENDED_BUNDLE)
    weekly = _load(WEEKLY)
    ops = _load(OPS)

    integrated_closure_ok = (
        all_gates_ok
        and full_ext.get("full_extension_closure_ok") is True
        and post_ext.get("observation_ok") is True
        and extended_bundle.get("extended_export_bundle_ok") is True
        and weekly.get("weekly_ok") is True
        and ops.get("closure_ok") is True
        and post_ext.get("weekly_task_ready") is True
    )

    return {
        "schema": "tkm_encounter_sequence_integrated_stack_closure_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "domain_lane": "tkm_korean_han_medicine",
        "send_gate": "HOLD",
        "non_gating": True,
        "research_only": True,
        "integrated_closure_ok": integrated_closure_ok,
        "gates": gates,
        "gates_ok_count": sum(1 for g in gates.values() if g.get("gate_ok") is True),
        "full_extension_closure_ok": full_ext.get("full_extension_closure_ok"),
        "post_extension_observation_ok": post_ext.get("observation_ok"),
        "extended_export_bundle_ok": extended_bundle.get("extended_export_bundle_ok"),
        "export_ingest_kpi_ok": post_ext.get("export_ingest_kpi_ok"),
        "weekly_task_ready": post_ext.get("weekly_task_ready"),
        "interpret_gpu_train_attempted": post_ext.get("interpret_gpu_train_attempted"),
        "curated_reviewed_count": full_ext.get("curated_reviewed_count"),
        "weekly_report_version": weekly.get("version"),
        "ops_closure_version": ops.get("version"),
        "ops_closure_ok": ops.get("closure_ok"),
        "stack_phases_ko": "P33–P49 extension stack → P50 post-extension obs → P51 integrated closure",
        "note_ko": "P33–P50 integrated stack closure [HYPO][NON_GATING]; Track A·auto-training·진단·처방 금지.",
        "reproduce": "py scripts/build_tkm_encounter_sequence_integrated_stack_closure_v1.py",
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
    print(json.dumps({"ok": doc.get("integrated_closure_ok"), "gates": doc.get("gates_ok_count")}))
    return 0 if doc.get("integrated_closure_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
