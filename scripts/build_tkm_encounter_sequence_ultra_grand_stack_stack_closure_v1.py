#!/usr/bin/env python3
"""Build TKM encounter_sequence ultra-grand stack closure rollup (P63–P67) [HYPO]."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/tkm_encounter_sequence_ultra_grand_stack_stack_closure_v1_latest.json"
ARTIFACT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_ultra_grand_stack_stack_closure_v1_latest.json"

GATE_KEYS = tuple(f"p{n}" for n in range(63, 68))
GATE_PATHS = {k: ROOT / f"docs/final/artifacts/tkm_encounter_sequence_{k}_gate_v1_latest.json" for k in GATE_KEYS}

ULTRA_GRAND_POST_EXPORT = ROOT / "reports/tkm_encounter_sequence_ultra_grand_post_export_closure_v1_latest.json"
ULTRA_GRAND_VAULT_SYNC = ROOT / "reports/tkm_encounter_sequence_ultra_grand_export_bundle_vault_sync_v1_latest.json"
POST_ULTRA_GRAND_OBS = ROOT / "reports/tkm_encounter_sequence_post_ultra_grand_passive_observation_v1_latest.json"
FULL_ULTRA_GRAND_CLOSURE = ROOT / "reports/tkm_encounter_sequence_full_ultra_grand_stack_final_closure_v1_latest.json"
ULTRA_GRAND_EXTENSION_BUNDLE = ROOT / "reports/tkm_encounter_sequence_ultra_grand_extension_export_bundle_v1_latest.json"
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
    ultra = _load(ULTRA_GRAND_POST_EXPORT)
    ultra_vault = _load(ULTRA_GRAND_VAULT_SYNC)
    post_ultra = _load(POST_ULTRA_GRAND_OBS)
    full_ultra = _load(FULL_ULTRA_GRAND_CLOSURE)
    bundle = _load(ULTRA_GRAND_EXTENSION_BUNDLE)
    weekly = _load(WEEKLY)
    ops = _load(OPS)

    ultra_grand_stack_stack_closure_ok = (
        all_gates_ok
        and ultra.get("ultra_grand_post_export_closure_ok") is True
        and ultra_vault.get("ultra_grand_export_bundle_vault_sync_ok") is True
        and post_ultra.get("observation_ok") is True
        and full_ultra.get("full_ultra_grand_stack_final_closure_ok") is True
        and bundle.get("ultra_grand_extension_export_bundle_ok") is True
        and weekly.get("weekly_ok") is True
        and ops.get("closure_ok") is True
        and int(post_ultra.get("curated_reviewed_count") or 0) >= 6
        and ultra_vault.get("cloud_upload_forbidden") is True
    )

    return {
        "schema": "tkm_encounter_sequence_ultra_grand_stack_stack_closure_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "domain_lane": "tkm_korean_han_medicine",
        "send_gate": "HOLD",
        "non_gating": True,
        "research_only": True,
        "ultra_grand_stack_stack_closure_ok": ultra_grand_stack_stack_closure_ok,
        "ultra_grand_stack_breakpoint_freeze": ultra_grand_stack_stack_closure_ok,
        "gates": gates,
        "gates_ok_count": sum(1 for g in gates.values() if g.get("gate_ok") is True),
        "ultra_grand_post_export_closure_ok": ultra.get("ultra_grand_post_export_closure_ok"),
        "ultra_grand_export_bundle_vault_sync_ok": ultra_vault.get("ultra_grand_export_bundle_vault_sync_ok"),
        "post_ultra_grand_passive_observation_ok": post_ultra.get("observation_ok"),
        "full_ultra_grand_stack_final_closure_ok": full_ultra.get("full_ultra_grand_stack_final_closure_ok"),
        "ultra_grand_extension_export_bundle_ok": bundle.get("ultra_grand_extension_export_bundle_ok"),
        "interpret_gpu_train_attempted": post_ultra.get("interpret_gpu_train_attempted"),
        "curated_reviewed_count": post_ultra.get("curated_reviewed_count"),
        "curated_pending_human_review": post_ultra.get("curated_pending_human_review"),
        "manifest_files_present_count": ultra_vault.get("manifest_files_present_count"),
        "weekly_report_version": weekly.get("version"),
        "ops_closure_version": ops.get("version"),
        "ops_closure_ok": ops.get("closure_ok"),
        "stack_phases_ko": "P63 ultra closure → P64 vault sync → P65 post-ultra obs → P66 final closure → P67 extension export → P68 ultra-grand stack closure",
        "note_ko": "P63–P67 ultra-grand stack closure [HYPO][NON_GATING]; B-track breakpoint freeze; Track A·auto-training·진단·처방 금지.",
        "reproduce": "py scripts/build_tkm_encounter_sequence_ultra_grand_stack_stack_closure_v1.py",
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
    print(json.dumps({"ok": doc.get("ultra_grand_stack_stack_closure_ok"), "gates": doc.get("gates_ok_count")}))
    return 0 if doc.get("ultra_grand_stack_stack_closure_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
