#!/usr/bin/env python3
"""Build TKM encounter_sequence grand-stack stack closure rollup (P57–P61) [HYPO]."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/tkm_encounter_sequence_grand_stack_stack_closure_v1_latest.json"
ARTIFACT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_grand_stack_stack_closure_v1_latest.json"

GATE_KEYS = tuple(f"p{n}" for n in range(57, 62))
GATE_PATHS = {k: ROOT / f"docs/final/artifacts/tkm_encounter_sequence_{k}_gate_v1_latest.json" for k in GATE_KEYS}

GRAND_POST_EXPORT = ROOT / "reports/tkm_encounter_sequence_grand_post_export_closure_v1_latest.json"
GRAND_VAULT_SYNC = ROOT / "reports/tkm_encounter_sequence_grand_export_bundle_vault_sync_v1_latest.json"
POST_GRAND_OBS = ROOT / "reports/tkm_encounter_sequence_post_grand_passive_observation_v1_latest.json"
FULL_GRAND_CLOSURE = ROOT / "reports/tkm_encounter_sequence_full_grand_stack_final_closure_v1_latest.json"
GRAND_EXTENSION_BUNDLE = ROOT / "reports/tkm_encounter_sequence_grand_stack_extension_export_bundle_v1_latest.json"
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
    grand = _load(GRAND_POST_EXPORT)
    grand_vault = _load(GRAND_VAULT_SYNC)
    post_grand = _load(POST_GRAND_OBS)
    full_grand = _load(FULL_GRAND_CLOSURE)
    bundle = _load(GRAND_EXTENSION_BUNDLE)
    weekly = _load(WEEKLY)
    ops = _load(OPS)

    grand_stack_stack_closure_ok = (
        all_gates_ok
        and grand.get("grand_post_export_closure_ok") is True
        and grand_vault.get("grand_export_bundle_vault_sync_ok") is True
        and post_grand.get("observation_ok") is True
        and full_grand.get("full_grand_stack_final_closure_ok") is True
        and bundle.get("grand_stack_extension_export_bundle_ok") is True
        and weekly.get("weekly_ok") is True
        and ops.get("closure_ok") is True
        and int(post_grand.get("curated_reviewed_count") or 0) >= 6
        and grand_vault.get("cloud_upload_forbidden") is True
    )

    return {
        "schema": "tkm_encounter_sequence_grand_stack_stack_closure_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "domain_lane": "tkm_korean_han_medicine",
        "send_gate": "HOLD",
        "non_gating": True,
        "research_only": True,
        "grand_stack_stack_closure_ok": grand_stack_stack_closure_ok,
        "gates": gates,
        "gates_ok_count": sum(1 for g in gates.values() if g.get("gate_ok") is True),
        "grand_post_export_closure_ok": grand.get("grand_post_export_closure_ok"),
        "grand_export_bundle_vault_sync_ok": grand_vault.get("grand_export_bundle_vault_sync_ok"),
        "post_grand_passive_observation_ok": post_grand.get("observation_ok"),
        "full_grand_stack_final_closure_ok": full_grand.get("full_grand_stack_final_closure_ok"),
        "grand_stack_extension_export_bundle_ok": bundle.get("grand_stack_extension_export_bundle_ok"),
        "interpret_gpu_train_attempted": post_grand.get("interpret_gpu_train_attempted"),
        "curated_reviewed_count": post_grand.get("curated_reviewed_count"),
        "curated_pending_human_review": post_grand.get("curated_pending_human_review"),
        "manifest_files_present_count": grand_vault.get("manifest_files_present_count"),
        "weekly_report_version": weekly.get("version"),
        "ops_closure_version": ops.get("version"),
        "ops_closure_ok": ops.get("closure_ok"),
        "stack_phases_ko": "P57 grand closure → P58 vault sync → P59 post-grand obs → P60 final closure → P61 extension export → P62 grand-stack stack closure",
        "note_ko": "P57–P61 grand-stack stack closure [HYPO][NON_GATING]; Track A·auto-training·진단·처방 금지.",
        "reproduce": "py scripts/build_tkm_encounter_sequence_grand_stack_stack_closure_v1.py",
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
    print(json.dumps({"ok": doc.get("grand_stack_stack_closure_ok"), "gates": doc.get("gates_ok_count")}))
    return 0 if doc.get("grand_stack_stack_closure_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
