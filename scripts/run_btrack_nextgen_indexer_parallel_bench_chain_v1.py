#!/usr/bin/env python3
"""B-track [HYPO] parallel bench chain: charter + frozen snapshot + optional legacy/GPU steps."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHARTER_SCRIPT = ROOT / "scripts/build_btrack_nextgen_indexer_charter_v1.py"
CHARTER_JSON = ROOT / "reports/btrack_nextgen_indexer_charter_v1_latest.json"
OUT = ROOT / "reports/btrack_nextgen_indexer_parallel_bench_v1_latest.json"
ACTIVE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p.resolve()).replace("\\", "/")


def _run_py(script_rel: str, extra: list[str] | None = None) -> dict:
    cmd = [sys.executable, str(ROOT / script_rel)] + (extra or [])
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    return {
        "command": " ".join(cmd),
        "exit_code": proc.returncode,
        "stdout_tail": (proc.stdout or "")[-800:],
        "stderr_tail": (proc.stderr or "")[-400:],
    }


def _frozen_row() -> dict:
    if not ACTIVE.is_file():
        return {"present": False}
    doc = json.loads(ACTIVE.read_text(encoding="utf-8"))
    cm = doc.get("compression_metrics") or {}
    return {
        "present": True,
        "global_token_saving_rate": cm.get("global_token_saving_rate"),
        "avg_reconstruction_fidelity_jaccard": cm.get("avg_reconstruction_fidelity_jaccard"),
        "alignment_pass_rate_raw": cm.get("alignment_pass_rate_raw"),
        "alignment_pass_rate_repair_v2": cm.get("alignment_pass_rate_repair_v2")
        or cm.get("alignment_pass_rate"),
    }


def _beat_check(candidate: dict | None, frozen: dict) -> dict:
    if not candidate or not frozen.get("present"):
        return {"beat_frozen": False, "reason": "missing_candidate_or_frozen"}
    saving_c = candidate.get("global_token_saving_rate")
    jacc_c = candidate.get("avg_reconstruction_fidelity_jaccard")
    saving_f = frozen.get("global_token_saving_rate")
    jacc_f = frozen.get("avg_reconstruction_fidelity_jaccard")
    if None in (saving_c, jacc_c, saving_f, jacc_f):
        return {"beat_frozen": False, "reason": "incomplete_metrics"}
    beat = saving_c >= saving_f and jacc_c >= jacc_f
    return {
        "beat_frozen": beat,
        "delta_saving_pp": round((saving_c - saving_f) * 100, 2),
        "delta_jaccard_pp": round((jacc_c - jacc_f) * 100, 2),
        "reason": "both_saving_and_jaccard_gte_frozen" if beat else "not_both_axes",
    }


def build_plan(execute: bool) -> dict:
    frozen = _frozen_row()
    steps = [
        {
            "step_id": "S1_charter",
            "arm_id": None,
            "script": _rel(CHARTER_SCRIPT),
            "mode": "always",
            "description": "Materialize nextgen indexer charter JSON",
        },
        {
            "step_id": "S2_legacy_ablation",
            "arm_id": "legacy_discrete_41k",
            "script": "scripts/comp_atom02_lexicon_must_keep_analysis_v1.py",
            "mode": "execute_only",
            "description": "41k ON/OFF ablation on V2 bench (existing)",
        },
        {
            "step_id": "S3_gpu_semantic",
            "arm_id": "gpu_semantic_poc",
            "script": "scripts/run_en_tech_semantic_gpu_poc_v1.py",
            "mode": "execute_only",
            "description": "GPU semantic PoC (skip if infra missing; non-fatal)",
            "optional": True,
        },
        {
            "step_id": "S4_nextgen_latent",
            "arm_id": "nextgen_latent_indexer",
            "script": "scripts/run_nextgen_clean_slate_cpu_sandbox_chain_v1.py",
            "mode": "execute_only",
            "description": "CPU clean-slate sandbox (topology+RTT+P0+P1+NG baseline)",
            "optional": False,
            "extra_args": [
                "--execute",
                "--main-only",
            ],
        },
    ]

    results: list[dict] = []
    for step in steps:
        row: dict = {"step_id": step["step_id"], "status": "planned"}
        if step["mode"] == "blocked":
            row["status"] = "not_implemented"
            row["note"] = step["description"]
            results.append(row)
            continue
        if step["step_id"] == "S1_charter":
            if execute:
                row.update(_run_py(_rel(CHARTER_SCRIPT)))
                row["status"] = "ok" if row["exit_code"] == 0 else "fail"
            else:
                row["status"] = "dry_run"
            results.append(row)
            continue
        if not execute:
            row["status"] = "dry_run_skipped"
            results.append(row)
            continue
        script = step.get("script")
        if not script:
            results.append(row)
            continue
        script_path = ROOT / script.replace("/", "\\")
        if not script_path.is_file():
            row["status"] = "skipped_missing_script"
            results.append(row)
            continue
        row.update(_run_py(script, step.get("extra_args")))
        if step.get("optional") and row["exit_code"] != 0:
            row["status"] = "optional_fail"
        else:
            row["status"] = "ok" if row["exit_code"] == 0 else "fail"
        results.append(row)

    charter = {}
    if CHARTER_JSON.is_file():
        charter = json.loads(CHARTER_JSON.read_text(encoding="utf-8"))

    gpu_metrics = None
    gpu_path = (
        ROOT
        / "reports/constitution/btrack_pilot/comp_en_tech_semantic_gpu_poc_local_v1_latest.json"
    )
    if gpu_path.is_file():
        gdoc = json.loads(gpu_path.read_text(encoding="utf-8"))
        gpu_metrics = gdoc.get("summary") or gdoc.get("compression_metrics") or gdoc

    ng_baseline_path = (
        ROOT
        / "experiments/nextgen_clean_slate_cpu_v1/results/nextgen_neural_baseline_v1_latest.json"
    )
    ng40_path = (
        ROOT
        / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_latent_stub_shadow_v1_latest.json"
    )
    ng40_poc_path = (
        ROOT
        / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_latent_poc_v1_latest.json"
    )
    ng40_eval_best = (
        ROOT
        / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_latent_eval_best_v1_latest.json"
    )
    ng40_sweep = (
        ROOT
        / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_latent_eval_cap_sweep_v1_latest.json"
    )
    ng40_hybrid = (
        ROOT
        / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_latent_poc_eval_hybrid_v1_latest.json"
    )
    ng40_ablation = (
        ROOT
        / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_lexicon_ablation_v1_latest.json"
    )
    ng_metrics = None
    ng_status = "charter_only"
    ng_beat = {
        "beat_frozen": False,
        "reason": "ng_baseline_not_golden40_compatible",
    }
    if ng_baseline_path.is_file():
        ng_doc = json.loads(ng_baseline_path.read_text(encoding="utf-8-sig"))
        ng_metrics = ng_doc.get("measurements_summary")
        phase = ng_doc.get("implementation_phase") or "partial_poc"
        ng_status = "partial_poc" if phase else "charter_only"
    elif execute and any(
        s.get("step_id") == "S4_nextgen_latent" and s.get("status") == "ok"
        for s in results
    ):
        ng_status = "partial_poc"
    if ng40_eval_best.is_file():
        ev_doc = json.loads(ng40_eval_best.read_text(encoding="utf-8-sig"))
        ev_agg = ev_doc.get("aggregate") or {}
        ng_metrics = {
            "infra_baseline": ng_metrics,
            "ng40_eval_best": ev_agg,
            "ng40_eval_beat_check": ev_doc.get("beat_check"),
            "golden40_compatible": ev_doc.get("golden40_compatible"),
        }
        if ng40_sweep.is_file():
            sw = json.loads(ng40_sweep.read_text(encoding="utf-8-sig"))
            ng_metrics["cap_sweep_any_beat"] = sw.get("any_beat_frozen")
            ng_metrics["cap_sweep_combo_count"] = sw.get("combo_count")
        if ng40_ablation.is_file():
            ab = json.loads(ng40_ablation.read_text(encoding="utf-8-sig"))
            ng_metrics["lexicon_ablation"] = ab.get("attribution")
            ng_metrics["lexicon_ablation_arms"] = [
                {
                    "arm_id": a.get("arm_id"),
                    "beat_frozen": (a.get("beat_check") or {}).get("beat_frozen"),
                    "saving": (a.get("aggregate") or {}).get("global_token_saving_rate"),
                    "jaccard": (a.get("aggregate") or {}).get(
                        "avg_reconstruction_fidelity_jaccard"
                    ),
                }
                for a in ab.get("arms") or []
            ]
        ng_status = "partial_poc"
        ng_beat = {
            **(ev_doc.get("beat_check") or {}),
            "reason": (ev_doc.get("beat_check") or {}).get("reason")
            or "ng40_eval_best_measured",
            "note": "NG-40 eval cap lane (41k OFF); primary beat evidence",
        }
    if ng40_hybrid.is_file():
        hy_doc = json.loads(ng40_hybrid.read_text(encoding="utf-8-sig"))
        ng_metrics = dict(ng_metrics or {})
        ng_metrics["poc_eval_hybrid"] = {
            "eval": (hy_doc.get("eval_lane") or {}).get("aggregate"),
            "poc": (hy_doc.get("poc_lane") or {}).get("aggregate"),
            "oracle_jaccard_avg": (hy_doc.get("oracle_jaccard_upper_bound") or {})
            .get("aggregate", {})
            .get("avg_reconstruction_fidelity_jaccard"),
            "caps": hy_doc.get("eval_caps"),
        }
    if ng40_poc_path.is_file():
        poc_doc = json.loads(ng40_poc_path.read_text(encoding="utf-8-sig"))
        poc_agg = poc_doc.get("aggregate") or {}
        ng_metrics = dict(ng_metrics or {})
        ng_metrics.update(
            {
                "infra_baseline": ng_metrics.get("infra_baseline") or ng_metrics,
                "ng40_latent_poc": poc_agg,
                "ng40_poc_beat_check": poc_doc.get("beat_check"),
                "ng40_poc_selected_keep_ratio": poc_doc.get("selected_keep_ratio"),
            }
        )
        ng_status = "partial_poc"
        if not (ng_beat or {}).get("beat_frozen"):
            ng_beat = {
                **(poc_doc.get("beat_check") or {}),
                "reason": (poc_doc.get("beat_check") or {}).get("reason")
                or "ng40_latent_poc_measured",
                "note": "P2b salience PoC; Jaccard near frozen at high keep_ratio; saving tradeoff",
            }
    elif ng40_path.is_file() and not ng40_eval_best.is_file():
        ng40_doc = json.loads(ng40_path.read_text(encoding="utf-8-sig"))
        agg = ng40_doc.get("aggregate") or {}
        ng_metrics = {
            "infra_baseline": ng_metrics,
            "ng40_shadow": agg,
            "ng40_beat_check": ng40_doc.get("beat_check"),
            "golden40_compatible": ng40_doc.get("golden40_compatible"),
        }
        ng_status = "partial_poc"
        ng_beat = {
            **(ng40_doc.get("beat_check") or {}),
            "reason": (
                (ng40_doc.get("beat_check") or {}).get("reason")
                or "ng40_shadow_measured"
            ),
            "note": "P2 stub on Golden-40; not neural E2E; ACTIVE overwrite forbidden",
        }

    summary = {
        "schema": "btrack_nextgen_indexer_parallel_bench_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "execute": execute,
        "frozen_baseline": frozen,
        "arms": {
            "legacy_discrete_41k": {
                "status": "frozen_reference",
                "metrics": frozen,
                "beat_check": {"beat_frozen": True, "reason": "is_baseline"},
            },
            "gpu_semantic_poc": {
                "status": "partial_poc",
                "metrics": gpu_metrics,
                "beat_check": _beat_check(
                    gpu_metrics if isinstance(gpu_metrics, dict) else None, frozen
                ),
            },
            "nextgen_latent_indexer": {
                "status": ng_status,
                "metrics": ng_metrics,
                "beat_check": ng_beat,
                "baseline_pointer": (
                    str(ng_baseline_path.relative_to(ROOT)).replace("\\", "/")
                    if ng_baseline_path.is_file()
                    else None
                ),
                "ng40_shadow_pointer": (
                    str(ng40_path.relative_to(ROOT)).replace("\\", "/")
                    if ng40_path.is_file()
                    else None
                ),
                "ng40_latent_poc_pointer": (
                    str(ng40_poc_path.relative_to(ROOT)).replace("\\", "/")
                    if ng40_poc_path.is_file()
                    else None
                ),
                "ng40_eval_best_pointer": (
                    str(ng40_eval_best.relative_to(ROOT)).replace("\\", "/")
                    if ng40_eval_best.is_file()
                    else None
                ),
                "ng40_cap_sweep_pointer": (
                    str(ng40_sweep.relative_to(ROOT)).replace("\\", "/")
                    if ng40_sweep.is_file()
                    else None
                ),
                "ng40_lexicon_ablation_pointer": (
                    str(ng40_ablation.relative_to(ROOT)).replace("\\", "/")
                    if ng40_ablation.is_file()
                    else None
                ),
            },
        },
        "steps": results,
        "charter_pointer": _rel(CHARTER_JSON) if CHARTER_JSON.is_file() else None,
        "promotion_status": "research_only",
        "track_a_active_write": False,
    }
    if charter:
        summary["branch_name"] = charter.get("branch_name")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Emit plan only (default if neither --execute nor --json-plan)",
    )
    parser.add_argument("--execute", action="store_true", help="Run safe subprocess steps")
    parser.add_argument("--json-plan", action="store_true", help="Print plan JSON to stdout")
    args = parser.parse_args()

    execute = bool(args.execute)
    if not execute and not args.json_plan and not args.dry_run:
        args.dry_run = True

    doc = build_plan(execute=execute)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.json_plan:
        print(json.dumps(doc, ensure_ascii=False, indent=2))
    else:
        print(
            json.dumps(
                {
                    "wrote": str(OUT),
                    "execute": execute,
                    "nextgen_arm": doc["arms"]["nextgen_latent_indexer"]["status"],
                },
                ensure_ascii=False,
            )
        )

    hard_fail = any(s.get("status") == "fail" for s in doc["steps"])
    return 1 if hard_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
