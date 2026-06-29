#!/usr/bin/env python3
"""[HYPO] DR Phase 4 — conditional fusion ablation stack (proxy v1 → codec v2 → SSOT v3).

Wires compression multilens research chain end-to-end.
research_only · send_gate HOLD · never --apply-active.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
OUT = ROOT / "reports/ng40_dr_phase4_conditional_fusion_completion_chain_v1_latest.json"
ACTIVE_CODEC_CACHE = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_conditional_fusion_active_arm_v1_latest.report.json"
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(step_id: str, cmd: list[str]) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    return {
        "id": step_id,
        "cmd": cmd,
        "exit_code": int(proc.returncode),
        "stdout_tail": (proc.stdout or "")[-1500:],
        "stderr_tail": (proc.stderr or "")[-800:],
    }


def _load(rel: str) -> dict[str, Any] | None:
    p = ROOT / rel.replace("/", "\\")
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-routing-manifest", action="store_true")
    ap.add_argument("--skip-knee-summary", action="store_true")
    ap.add_argument("--skip-proxy-v1", action="store_true")
    ap.add_argument("--skip-codec-v2", action="store_true")
    ap.add_argument("--skip-ssot-v3", action="store_true")
    ap.add_argument("--skip-pytest", action="store_true")
    ap.add_argument("--force-codec-rerun", action="store_true")
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []

    if not args.skip_routing_manifest:
        steps.append(
            _run(
                "routing_confidence_manifest",
                [PY, "scripts/build_compression_routing_confidence_ng40_manifest_v1.py"],
            )
        )

    if not args.skip_knee_summary:
        steps.append(_run("path_b_knee_summary", [PY, "scripts/build_ng40_path_b_knee_summary_v1.py"]))

    if not args.skip_proxy_v1:
        steps.append(
            _run(
                "conditional_fusion_proxy_v1",
                [PY, "scripts/run_compression_conditional_fusion_ablation_v1.py", "--holdout-frac", "0.2"],
            )
        )

    if not args.skip_codec_v2:
        v2_cmd = [
            PY,
            "scripts/run_compression_conditional_fusion_ablation_v2_codec_rerun_v1.py",
            "--holdout-frac",
            "0.2",
        ]
        if not args.force_codec_rerun and ACTIVE_CODEC_CACHE.is_file():
            v2_cmd.append("--skip-codec-rerun")
        steps.append(_run("conditional_fusion_codec_v2", v2_cmd))

    if not args.skip_ssot_v3:
        v3_cmd = [
            PY,
            "scripts/run_compression_conditional_fusion_ablation_v3_ssot_guard_codec_rerun_v1.py",
            "--holdout-frac",
            "0.2",
        ]
        if args.force_codec_rerun:
            v3_cmd.append("--force-codec-rerun")
        steps.append(_run("conditional_fusion_ssot_v3", v3_cmd))

    if not args.skip_pytest:
        steps.append(
            _run(
                "pytest_conditional_fusion_smoke",
                [
                    PY,
                    "-m",
                    "pytest",
                    "tests/test_compression_conditional_fusion_ablation_v1.py",
                    "tests/test_compression_conditional_fusion_ablation_v2_codec_rerun_v1.py",
                    "tests/test_compression_conditional_fusion_ablation_v3_ssot_guard_v1.py",
                    "-q",
                ],
            )
        )

    failed = [s for s in steps if s["exit_code"] != 0]
    v1 = _load("reports/compression_conditional_fusion_ablation_v1_latest.json")
    v2 = _load("reports/compression_conditional_fusion_ablation_v2_codec_rerun_v1_latest.json")
    v3 = _load("reports/compression_conditional_fusion_ablation_v3_ssot_guard_v1_latest.json")
    topology = _load(
        "docs/final/artifacts/logos_topology_sidecar_compression_improvement_multilens_v1_latest.json"
    )

    v3_cond = (v3 or {}).get("golden40_codec_arms", {}).get("conditional_merged") or {}
    v2_cond = (v2 or {}).get("golden40_codec_arms", {}).get("conditional_merged") or {}
    active = (v2 or {}).get("golden40_codec_arms", {}).get("active_global") or {}

    doc: dict[str, Any] = {
        "schema": "ng40_dr_phase4_conditional_fusion_completion_chain_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "send_gate": "HOLD",
        "track_a_active_write": False,
        "apply_forbidden": True,
        "chain_ok": len(failed) == 0,
        "failed_steps": [s["id"] for s in failed],
        "steps": steps,
        "conditional_fusion_stack": {
            "v1_proxy_uplift_holdout": (v1 or {}).get("uplift_signal_holdout"),
            "v2_codec_beat_frozen": (v2 or {}).get("beat_check_conditional_vs_frozen", {}).get("beat_frozen"),
            "v2_codec_min_j": v2_cond.get("min_reconstruction_fidelity_jaccard"),
            "v3_ssot_recommended": (v3 or {}).get("recommended_policy"),
            "v3_codec_beat_frozen": (v3 or {}).get("beat_check_conditional_vs_frozen", {}).get("beat_frozen"),
            "v3_codec_min_j": v3_cond.get("min_reconstruction_fidelity_jaccard"),
            "v3_codec_saving": v3_cond.get("global_token_saving_rate"),
            "v3_knee_j_guard_count": (v3 or {}).get("policy_counts", {}).get("knee_j_guard"),
            "v3_vs_v2_saving_pp": (v3 or {}).get("v2_compare", {}).get("v3_minus_v2_saving_pp"),
            "active_baseline_min_j": active.get("min_reconstruction_fidelity_jaccard"),
        },
        "headline_ko": {
            "latent_research": (
                f"conditional v3 SSOT-guard: saving {v3_cond.get('global_token_saving_rate', 0):.4f} "
                f"minJ {v3_cond.get('min_reconstruction_fidelity_jaccard', 0):.4f} "
                f"(active minJ {active.get('min_reconstruction_fidelity_jaccard', 0):.4f})"
            ),
            "product_b2b": "Path A spine ~22.29% byte_exact — unchanged honest KPI",
            "promotion": "beat_frozen false — apply_active HOLD",
        },
        "topology_sidecar": {
            "present": bool(topology),
            "query_id": (topology or {}).get("query_id"),
            "send_gate": (topology or {}).get("send_gate"),
        },
        "pointers": {
            "multilens_lit": "docs/research/COMPRESSION_IMPROVEMENT_MULTILENS_DEEP_RESEARCH_LIT_REVIEW_2026-06-22.md",
            "v1_proxy": "reports/compression_conditional_fusion_ablation_v1_latest.json",
            "v2_codec": "reports/compression_conditional_fusion_ablation_v2_codec_rerun_v1_latest.json",
            "v3_ssot": "reports/compression_conditional_fusion_ablation_v3_ssot_guard_v1_latest.json",
            "phase3_chain": "reports/ng40_dr_phase3_completion_chain_v1_latest.json",
            "topology_sidecar": (
                "docs/final/artifacts/logos_topology_sidecar_compression_improvement_multilens_v1_latest.json"
            ),
        },
        "reproducible_command": "py scripts/run_ng40_dr_phase4_conditional_fusion_completion_chain_v1.py",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"chain_ok": doc["chain_ok"], "failed_steps": doc["failed_steps"]}, ensure_ascii=False))
    return 0 if doc["chain_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
