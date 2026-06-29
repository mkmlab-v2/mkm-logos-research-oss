#!/usr/bin/env python3
"""Build TKM encounter_sequence P43 GPU+passive+curated observability rollup [HYPO]."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/tkm_encounter_sequence_p43_observability_rollup_v1_latest.json"
ARTIFACT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p43_observability_rollup_v1_latest.json"

P42_BUNDLE = ROOT / "reports/tkm_encounter_sequence_full_stack_export_bundle_v1_latest.json"
PASSIVE = ROOT / "reports/tkm_encounter_sequence_passive_observation_v1_latest.json"
INTERPRET = ROOT / "reports/myeongri_interpret_micro_retrain_chain_v1_latest.json"
REVIEW_MARK = ROOT / "reports/encounter_sequence_curated_review_mark_v1_latest.json"
P42_GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p42_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build() -> dict[str, Any]:
    bundle = _load(P42_BUNDLE)
    passive = _load(PASSIVE)
    interpret = _load(INTERPRET)
    review = _load(REVIEW_MARK)
    p42 = _load(P42_GATE)
    review_counts = review.get("review_counts") if isinstance(review.get("review_counts"), dict) else {}

    interpret_cpu_ok = interpret.get("cpu_guard_ok") is True or not INTERPRET.is_file()
    interpret_gpu_attempted = interpret.get("gpu_train_attempted") is True
    interpret_gpu_ok = interpret.get("gpu_train_ok") if interpret_gpu_attempted else None
    gpu_obs_ok = interpret_gpu_ok is True if interpret_gpu_attempted else interpret_cpu_ok

    observability_ok = (
        p42.get("gate_ok") is True
        and bundle.get("export_bundle_ok") is True
        and passive.get("observation_ok") is True
        and interpret_cpu_ok
        and gpu_obs_ok
        and review.get("ok") is True
        and int(review_counts.get("reviewed") or 0) >= 1
    )

    return {
        "schema": "tkm_encounter_sequence_p43_observability_rollup_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "domain_lane": "tkm_korean_han_medicine",
        "send_gate": "HOLD",
        "non_gating": True,
        "research_only": True,
        "observability_ok": observability_ok,
        "full_stack_export_bundle_ok": bundle.get("export_bundle_ok"),
        "passive_observation_ok": passive.get("observation_ok"),
        "interpret_cpu_guard_ok": interpret_cpu_ok,
        "interpret_gpu_train_attempted": interpret_gpu_attempted,
        "interpret_gpu_train_ok": interpret_gpu_ok,
        "interpret_gpu_skipped_reason": interpret.get("gpu_train_skipped_reason"),
        "curated_review_mark_ok": review.get("ok"),
        "curated_review_marked_count": review.get("marked_count"),
        "curated_review_counts": review_counts,
        "auto_training_forbidden": True,
        "note_ko": "P43 GPU+passive+curated observability [HYPO][NON_GATING]; auto-training·Track A 금지.",
        "reproduce": "py scripts/build_tkm_encounter_sequence_p43_observability_rollup_v1.py",
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
    print(json.dumps({"ok": doc.get("observability_ok"), "reviewed": (doc.get("curated_review_counts") or {}).get("reviewed")}))
    return 0 if doc.get("observability_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
