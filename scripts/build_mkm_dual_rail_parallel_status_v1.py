#!/usr/bin/env python3
"""Roll up parallel rail status: compression_41k vs prophecy_shadow_31k ([HYPO], no active write)."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports/mkm_dual_rail_parallel_status_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _rel(p: Path) -> str:
    return str(p.relative_to(ROOT)).replace("\\", "/")


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--run-parallel-smoke", action="store_true")
    ap.add_argument("--run-31k", action="store_true")
    ap.add_argument("--run-41k-audit", action="store_true")
    ap.add_argument("--run-gpu-bundle", action="store_true", help="Slow: Run-MkmGpuRecommendedBundle")
    args = ap.parse_args()

    steps: list[dict] = []

    def _step(cmd: list[str], step_id: str) -> None:
        proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
        steps.append(
            {
                "step_id": step_id,
                "rail_id": "compression_41k"
                if "41k" in step_id or "compression" in step_id or "gpu" in step_id
                else "prophecy_shadow_31k"
                if "31k" in step_id
                else "cross_cutting",
                "exit_code": proc.returncode,
                "ok": proc.returncode == 0,
                "output_tail": ((proc.stdout or "") + (proc.stderr or ""))[-600:].strip(),
            }
        )

    if args.run_parallel_smoke:
        _step(
            [sys.executable, "scripts/build_mkm_gpu_hybrid_parallel_auto_smoke_v1.py", "--max-cases", "8"],
            "parallel_smoke_bundle",
        )
    if args.run_31k:
        _step(
            [
                sys.executable,
                "scripts/run_btrack_31k41k_prophecy_shadow_chain_v1.py",
                "--daily-fast",
                "--skip-gate",
            ],
            "rail_31k_daily_fast",
        )
    if args.run_41k_audit:
        _step([sys.executable, "scripts/build_lexicon_lookup_exception_audit_v1.py"], "rail_41k_lookup_audit")
        _step([sys.executable, "scripts/comp_atom02_lexicon_must_keep_analysis_v1.py"], "rail_41k_atom02_ablation")
    if args.run_gpu_bundle:
        _step(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                "scripts/Run-MkmGpuRecommendedBundle_v1.ps1",
            ],
            "rail_41k_gpu_recommended_bundle",
        )

    smoke = _load(ROOT / "reports/mkm_gpu_hybrid_parallel_auto_smoke_v1_latest.json")
    audit = _load(ROOT / "reports/lexicon_lookup_exception_audit_v1_latest.json")
    hybrid = _load(ROOT / "reports/mkm_gpu_hybrid_transition_spec_v1_latest.json")
    oov120 = _load(
        ROOT / "reports/constitution/btrack_pilot/comp_en_tech_semantic_gpu_poc_oov_patch_v1_latest.json"
    )

    doc = {
        "schema": "mkm_dual_rail_parallel_status_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "track_a_active_write": False,
        "hypo_label": "[HYPO]",
        "single_loop_merge_forbidden": True,
        "steps_executed_this_run": steps,
        "all_steps_ok": all(s["ok"] for s in steps) if steps else None,
        "rail_compression_41k": {
            "status": "parallel_active",
            "pointers": {
                "hybrid_spec": _rel(ROOT / "reports/mkm_gpu_hybrid_transition_spec_v1_latest.json"),
                "parallel_smoke": _rel(ROOT / "reports/mkm_gpu_hybrid_parallel_auto_smoke_v1_latest.json"),
                "lookup_audit": _rel(ROOT / "reports/lexicon_lookup_exception_audit_v1_latest.json"),
                "oov_resweep_120": _rel(
                    ROOT
                    / "reports/constitution/btrack_pilot/comp_en_tech_semantic_gpu_poc_oov_patch_v1_latest.json"
                ),
            },
            "metrics": {
                "golden40_ablation_delta": (smoke or {}).get(
                    "metrics_rollup", {}
                ).get("compression_41k_lexicon_ablation_delta_on_minus_off")
                or (audit or {}).get("compression_ablation_delta_on_minus_off"),
                "hangul_zero_hit_cases": (audit or {}).get("bucket_counts", {}).get(
                    "EXC_HANGUL_DOMINANT_ZERO_HIT"
                ),
                "en_tech_120_jaccard_min": (oov120 or {}).get("aggregate", {}).get("jaccard_min"),
            },
            "next_p0": "hangul tokenizer / cjk_bigram policy pilot (B-track, commander order)",
        },
        "rail_prophecy_shadow_31k": {
            "status": "parallel_active",
            "pointers": {
                "shadow_spec": _rel(
                    ROOT
                    / "docs/final/artifacts/btrack_31k41k_prophecy_shadow_experiment_spec_v1_latest.md"
                ),
                "fold_stability": _rel(
                    ROOT
                    / "docs/final/artifacts/btrack_31k41k_prophecy_shadow_fold_stability_v2b_strict_v1_latest.json"
                ),
            },
            "daily_fast_command": "py scripts/run_btrack_31k41k_prophecy_shadow_chain_v1.py --daily-fast",
            "vector_layer": "additive only — corpus_retire_forbidden",
        },
        "guardrails": (hybrid or {}).get("guardrails") or [],
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(OUT), "all_steps_ok": doc["all_steps_ok"]}, ensure_ascii=False))
    return 0 if doc["all_steps_ok"] is not False else 1


if __name__ == "__main__":
    raise SystemExit(main())
