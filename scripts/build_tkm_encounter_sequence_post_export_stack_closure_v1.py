#!/usr/bin/env python3
"""Build TKM encounter_sequence post-export stack closure rollup (P51–P55) [HYPO]."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/tkm_encounter_sequence_post_export_stack_closure_v1_latest.json"
ARTIFACT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_post_export_stack_closure_v1_latest.json"

GATE_KEYS = tuple(f"p{n}" for n in range(51, 56))
GATE_PATHS = {k: ROOT / f"docs/final/artifacts/tkm_encounter_sequence_{k}_gate_v1_latest.json" for k in GATE_KEYS}

INTEGRATED_CLOSURE = ROOT / "reports/tkm_encounter_sequence_integrated_stack_closure_v1_latest.json"
EXPORT_SYNC = ROOT / "reports/tkm_encounter_sequence_notebooklm_export_sync_v1_latest.json"
POST_EXPORT_OBS = ROOT / "reports/tkm_encounter_sequence_post_export_passive_observation_v1_latest.json"
FULL_POST_EXPORT = ROOT / "reports/tkm_encounter_sequence_full_post_export_closure_v1_latest.json"
POST_EXPORT_BUNDLE = ROOT / "reports/tkm_encounter_sequence_post_export_extended_export_bundle_v1_latest.json"
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
    integrated = _load(INTEGRATED_CLOSURE)
    export_sync = _load(EXPORT_SYNC)
    post_export = _load(POST_EXPORT_OBS)
    full_post = _load(FULL_POST_EXPORT)
    bundle = _load(POST_EXPORT_BUNDLE)
    weekly = _load(WEEKLY)
    ops = _load(OPS)

    post_export_stack_closure_ok = (
        all_gates_ok
        and integrated.get("integrated_closure_ok") is True
        and export_sync.get("export_sync_ok") is True
        and post_export.get("observation_ok") is True
        and full_post.get("full_post_export_closure_ok") is True
        and bundle.get("post_export_extended_export_bundle_ok") is True
        and weekly.get("weekly_ok") is True
        and ops.get("closure_ok") is True
        and int(post_export.get("curated_reviewed_count") or 0) >= 6
        and export_sync.get("cloud_upload_forbidden") is True
    )

    return {
        "schema": "tkm_encounter_sequence_post_export_stack_closure_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "domain_lane": "tkm_korean_han_medicine",
        "send_gate": "HOLD",
        "non_gating": True,
        "research_only": True,
        "post_export_stack_closure_ok": post_export_stack_closure_ok,
        "gates": gates,
        "gates_ok_count": sum(1 for g in gates.values() if g.get("gate_ok") is True),
        "integrated_closure_ok": integrated.get("integrated_closure_ok"),
        "export_sync_ok": export_sync.get("export_sync_ok"),
        "post_export_observation_ok": post_export.get("observation_ok"),
        "full_post_export_closure_ok": full_post.get("full_post_export_closure_ok"),
        "post_export_extended_export_bundle_ok": bundle.get("post_export_extended_export_bundle_ok"),
        "interpret_gpu_train_attempted": post_export.get("interpret_gpu_train_attempted"),
        "curated_reviewed_count": post_export.get("curated_reviewed_count"),
        "curated_pending_human_review": post_export.get("curated_pending_human_review"),
        "manifest_files_present_count": export_sync.get("manifest_files_present_count"),
        "weekly_report_version": weekly.get("version"),
        "ops_closure_version": ops.get("version"),
        "ops_closure_ok": ops.get("closure_ok"),
        "stack_phases_ko": "P51 integrated → P52 export sync → P53 post-export obs → P54 closure → P55 extended export → P56 post-export stack closure",
        "note_ko": "P51–P55 post-export stack closure [HYPO][NON_GATING]; Track A·auto-training·진단·처방 금지.",
        "reproduce": "py scripts/build_tkm_encounter_sequence_post_export_stack_closure_v1.py",
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
    print(json.dumps({"ok": doc.get("post_export_stack_closure_ok"), "gates": doc.get("gates_ok_count")}))
    return 0 if doc.get("post_export_stack_closure_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
