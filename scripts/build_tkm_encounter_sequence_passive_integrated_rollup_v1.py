#!/usr/bin/env python3
"""Build TKM encounter_sequence passive+interpret+curated integrated rollup (P40) [HYPO]."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/tkm_encounter_sequence_passive_integrated_rollup_v1_latest.json"
ARTIFACT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_passive_integrated_rollup_v1_latest.json"

PASSIVE = ROOT / "reports/tkm_encounter_sequence_passive_observation_v1_latest.json"
INTERPRET = ROOT / "reports/myeongri_interpret_micro_retrain_chain_v1_latest.json"
ACK = ROOT / "reports/encounter_sequence_curated_learning_ack_v1_latest.json"
DRAFTS = ROOT / "docs/final/artifacts/encounter_sequence_curated_learning_draft_v1_latest.json"
REGISTRY = ROOT / "data/clinic/encounter_sequence_curated_learning_registry_v1.jsonl"
LENS_ROLLUP = ROOT / "reports/tkm_encounter_sequence_lens_stack_rollup_v1_latest.json"
P39_GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p39_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _registry_row_count() -> int:
    if not REGISTRY.is_file():
        return 0
    return sum(1 for line in REGISTRY.read_text(encoding="utf-8").splitlines() if line.strip())


def build() -> dict[str, Any]:
    passive = _load(PASSIVE)
    interpret = _load(INTERPRET)
    ack = _load(ACK)
    drafts = _load(DRAFTS)
    lens = _load(LENS_ROLLUP)
    p39 = _load(P39_GATE)
    registry_rows = _registry_row_count()

    interpret_cpu_ok = interpret.get("cpu_guard_ok") is True or not INTERPRET.is_file()
    interpret_gpu_attempted = interpret.get("gpu_train_attempted") is True
    interpret_gpu_ok = interpret.get("gpu_train_ok") if interpret_gpu_attempted else None
    curated_ack_ok = ack.get("ok") is True and ack.get("mode") == "human"
    passive_ok = passive.get("observation_ok") is True
    lens_rollup_ok = lens.get("rollup_ok") is True and p39.get("gate_ok") is True

    integrated_ok = (
        passive_ok
        and interpret_cpu_ok
        and curated_ack_ok
        and lens_rollup_ok
        and int(drafts.get("disagreement_draft_count") or len(drafts.get("drafts") or [])) >= 1
        and registry_rows >= 1
    )

    return {
        "schema": "tkm_encounter_sequence_passive_integrated_rollup_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "domain_lane": "tkm_korean_han_medicine",
        "send_gate": "HOLD",
        "non_gating": True,
        "integrated_ok": integrated_ok,
        "passive_observation_ok": passive_ok,
        "weekly_task_ready": passive.get("weekly_task_ready"),
        "interpret_cpu_guard_ok": interpret_cpu_ok,
        "interpret_gpu_train_attempted": interpret_gpu_attempted,
        "interpret_gpu_train_ok": interpret_gpu_ok,
        "interpret_gpu_skipped_reason": interpret.get("gpu_train_skipped_reason"),
        "curated_learning_ack_ok": curated_ack_ok,
        "curated_learning_ack_mode": ack.get("mode"),
        "disagreement_draft_count": drafts.get("disagreement_draft_count"),
        "curated_learning_registry_row_count": registry_rows,
        "lens_stack_rollup_ok": lens_rollup_ok,
        "cross_lens_resonance_index": passive.get("cross_lens_resonance_index"),
        "motif_top1_share": passive.get("motif_top1_share"),
        "motif_skew_gate_ok": passive.get("motif_skew_gate_ok"),
        "note_ko": "패시브+Interpret+curated 통합 rollup [HYPO][NON_GATING]; auto-training·Track A 금지.",
        "reproduce": "py scripts/build_tkm_encounter_sequence_passive_integrated_rollup_v1.py",
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
    print(json.dumps({"ok": doc.get("integrated_ok"), "registry_rows": doc.get("curated_learning_registry_row_count")}))
    return 0 if doc.get("integrated_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
