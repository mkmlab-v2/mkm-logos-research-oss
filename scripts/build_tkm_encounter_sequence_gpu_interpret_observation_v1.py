#!/usr/bin/env python3
"""Build TKM encounter_sequence P46 GPU+Interpret observability rollup [HYPO]."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/tkm_encounter_sequence_gpu_interpret_observation_v1_latest.json"
ARTIFACT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_gpu_interpret_observation_v1_latest.json"

P45_GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p45_gate_v1_latest.json"
MILESTONE = ROOT / "reports/tkm_encounter_sequence_curated_review_milestone_v1_latest.json"
PASSIVE = ROOT / "reports/tkm_encounter_sequence_passive_observation_v1_latest.json"
INTERPRET = ROOT / "reports/myeongri_interpret_micro_retrain_chain_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build() -> dict[str, Any]:
    p45 = _load(P45_GATE)
    milestone = _load(MILESTONE)
    passive = _load(PASSIVE)
    interpret = _load(INTERPRET)
    counts = milestone.get("curated_review_counts") if isinstance(milestone.get("curated_review_counts"), dict) else {}

    interpret_cpu_ok = interpret.get("cpu_guard_ok") is True or not INTERPRET.is_file()
    interpret_gpu_attempted = interpret.get("gpu_train_attempted") is True
    interpret_gpu_ok = interpret.get("gpu_train_ok") if interpret_gpu_attempted else None
    gpu_obs_ok = interpret_gpu_ok is True if interpret_gpu_attempted else interpret_cpu_ok

    observation_ok = (
        p45.get("gate_ok") is True
        and milestone.get("milestone_ok") is True
        and passive.get("observation_ok") is True
        and interpret_cpu_ok
        and gpu_obs_ok
        and int(counts.get("reviewed") or 0) >= int(milestone.get("milestone_reviewed_min") or 6)
    )

    return {
        "schema": "tkm_encounter_sequence_gpu_interpret_observation_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "domain_lane": "tkm_korean_han_medicine",
        "send_gate": "HOLD",
        "non_gating": True,
        "research_only": True,
        "observation_ok": observation_ok,
        "p45_gate_ok": p45.get("gate_ok"),
        "curated_milestone_ok": milestone.get("milestone_ok"),
        "passive_observation_ok": passive.get("observation_ok"),
        "interpret_cpu_guard_ok": interpret_cpu_ok,
        "interpret_gpu_train_attempted": interpret_gpu_attempted,
        "interpret_gpu_train_ok": interpret_gpu_ok,
        "interpret_gpu_skipped_reason": interpret.get("gpu_train_skipped_reason"),
        "curated_review_counts": counts,
        "auto_training_forbidden": True,
        "note_ko": "P46 GPU+Interpret observability [HYPO][NON_GATING]; CPU guard 기본·GPU optional; auto-training·Track A 금지.",
        "reproduce": "py scripts/build_tkm_encounter_sequence_gpu_interpret_observation_v1.py",
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
    print(
        json.dumps(
            {
                "ok": doc.get("observation_ok"),
                "gpu_attempted": doc.get("interpret_gpu_train_attempted"),
                "cpu_ok": doc.get("interpret_cpu_guard_ok"),
            }
        )
    )
    return 0 if doc.get("observation_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
