#!/usr/bin/env python3
"""[HYPO] Path B codec structure experiments: prior masks + 41k/trilane combos vs frozen ACTIVE."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ACTIVE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
OUT_MANIFEST = ROOT / "reports/ng40_path_b_structure_experiment_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(script: str, extra: list[str] | None = None) -> dict[str, Any]:
    cmd = [sys.executable, str(ROOT / script), *(extra or [])]
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    tail = (cp.stdout or "").strip().splitlines()
    parsed = None
    if tail:
        try:
            parsed = json.loads(tail[-1])
        except json.JSONDecodeError:
            parsed = {"raw_tail": tail[-1][:500]}
    return {
        "script": script,
        "args": extra or [],
        "exit_code": int(cp.returncode),
        "parsed": parsed,
    }


def _load(rel: str) -> dict[str, Any] | None:
    p = ROOT / rel.replace("/", "\\")
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8-sig"))


def _arm_summary(doc: dict[str, Any] | None) -> dict[str, Any] | None:
    if not doc:
        return None
    agg = doc.get("aggregate") or {}
    beat = doc.get("beat_check") or {}
    return {
        "arm_id": doc.get("arm_id") or doc.get("schema"),
        "lane": doc.get("lane"),
        "prior_terms_count": doc.get("prior_terms_count"),
        "saving": agg.get("global_token_saving_rate"),
        "jaccard": agg.get("avg_reconstruction_fidelity_jaccard"),
        "beat_frozen": beat.get("beat_frozen"),
        "byte_exact_parity": (doc.get("byte_exact_subset") or {}).get(
            "byte_exact_subset_parity"
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-diet", action="store_true")
    ap.add_argument("--skip-science-sidecar", action="store_true")
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    steps.append(_run("scripts/run_nextgen_phase3_archetype_prior_chain_v1.py"))
    steps.append(_run("scripts/run_nextgen_phase3_science_prior_mask_v1.py"))
    steps.append(_run("scripts/run_ng40_path_b_prior_41k_eval_v1.py"))
    steps.append(_run("scripts/run_ng40_path_b_trilane_prior_41k_eval_v1.py"))
    if not args.skip_science_sidecar:
        steps.append(_run("scripts/run_nextgen_science_prior_sidecar_chain_v1.py"))
    if not args.skip_diet:
        steps.append(_run("scripts/run_nextgen_prior_residual_diet_v1.py"))
    steps.append(_run("scripts/run_nextgen_coordinator_science_kernel_v2_chain_v1.py"))

    frozen_cm: dict[str, Any] = {}
    if ACTIVE.is_file():
        cm = json.loads(ACTIVE.read_text(encoding="utf-8-sig")).get("compression_metrics") or {}
        frozen_cm = {
            "global_token_saving_rate": cm.get("global_token_saving_rate"),
            "avg_reconstruction_fidelity_jaccard": cm.get(
                "avg_reconstruction_fidelity_jaccard"
            ),
        }

    arms = {
        "archetype_mask_41k_off": _arm_summary(
            _load(
                "experiments/nextgen_clean_slate_cpu_v1/results/"
                "ng40_latent_eval_archetype_prior_mask_v1_latest.json"
            )
        ),
        "trilane_mask_41k_off": _arm_summary(
            _load(
                "experiments/nextgen_clean_slate_cpu_v1/results/"
                "ng40_latent_eval_science_prior_mask_v1_latest.json"
            )
        ),
        "archetype_prior_41k_on": _arm_summary(
            _load(
                "experiments/nextgen_clean_slate_cpu_v1/results/"
                "ng40_latent_eval_path_b_prior_41k_v1_latest.json"
            )
        ),
        "trilane_prior_41k_on": _arm_summary(
            _load(
                "experiments/nextgen_clean_slate_cpu_v1/results/"
                "ng40_latent_eval_path_b_trilane_prior_41k_v1_latest.json"
            )
        ),
    }
    coord = _load(
        "experiments/nextgen_clean_slate_cpu_v1/results/"
        "ng40_coordinator_science_kernel_v2_chain_v1_latest.json"
    )
    coord_raw = (coord or {}).get("raw") or {}
    any_beat = any((a or {}).get("beat_frozen") for a in arms.values() if a) or bool(
        coord_raw.get("dual_axis_beat")
    )
    best_j = None
    best_arm = None
    for key, a in arms.items():
        if not a or a.get("jaccard") is None:
            continue
        j = float(a["jaccard"])
        if best_j is None or j > best_j:
            best_j = j
            best_arm = key

    manifest = {
        "schema": "ng40_path_b_structure_experiment_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "track_a_active_write": False,
        "frozen_active": frozen_cm,
        "arms": arms,
        "any_beat_frozen_dual_axis": any_beat,
        "best_jaccard_arm": best_arm,
        "coordinator_kernel_v2": {
            "closure_ok": (coord or {}).get("closure_ok"),
            "dual_axis_beat": coord_raw.get("dual_axis_beat"),
            "best_by_loss": coord_raw.get("best_by_loss"),
            "sweep_rows": coord_raw.get("sweep_rows"),
        },
        "conclusion_ko": (
            "구조 실험: cap이 아닌 must_keep 정책(아키타입 vs tri-lane) × 41k ON/OFF. "
            "dual-axis beat 없으면 codec/verbatim-spine 분리 유지."
            if not any_beat
            else "구조 arm에서 dual-axis beat 후보 — human sign-off·게이트 필수."
        ),
        "steps": steps,
        "forbidden": ["--apply-active", "shard_parallel_as_active_headline"],
        "next_if_no_beat": [
            "scripts/run_nextgen_coordinator_science_kernel_v2_chain_v1.py",
            "scripts/run_nextgen_prior_residual_diet_v1.py --refine",
        ],
    }
    manifest["research_only"] = True
    manifest["track_a_active_write"] = False

    OUT_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    OUT_MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "wrote": str(OUT_MANIFEST),
                "any_beat_frozen": any_beat,
                "best_jaccard_arm": best_arm,
            },
            ensure_ascii=False,
        )
    )
    hard = any(
        s["exit_code"] != 0
        for s in steps
        if s.get("script")
        in (
            "scripts/run_nextgen_phase3_archetype_prior_chain_v1.py",
            "scripts/run_nextgen_phase3_science_prior_mask_v1.py",
            "scripts/run_ng40_path_b_prior_41k_eval_v1.py",
            "scripts/run_ng40_path_b_trilane_prior_41k_eval_v1.py",
        )
    )
    return 1 if hard else 0


if __name__ == "__main__":
    raise SystemExit(main())
