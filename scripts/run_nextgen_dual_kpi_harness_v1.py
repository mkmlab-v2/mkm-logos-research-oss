#!/usr/bin/env python3
"""[HYPO] Dual-KPI harness: byte_exact + Jaccard/saving per arm (NG sandbox only)."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
OUT_DEFAULT = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_dual_kpi_harness_v1_latest.json"
)
BYTE_EXACT_OUT = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_byte_exact_subset_v1_latest.json"
)
SPINE_OUT = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_verbatim_spine_bench_v1_latest.json"
)
LOGOS_STACK_OUT = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_hybrid_spine_logos_stack_v1_latest.json"
)
PHASE3_OUT = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_latent_eval_archetype_prior_mask_v1_latest.json"
)
ACTIVE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
SALIENCE_HOOK = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_salience_hook_only.json"
)
NAV_FRAME = (
    ROOT / "experiments/nextgen_clean_slate_cpu_v1/ARCHETYPE_PRIOR_NAV_FRAME_V1.json"
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    try:
        return str(p.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p).replace("\\", "/")


def _frozen_baseline() -> dict[str, Any]:
    if not ACTIVE.is_file():
        return {"present": False, "label": "Track A ACTIVE (frozen)"}
    cm = json.loads(ACTIVE.read_text(encoding="utf-8")).get("compression_metrics") or {}
    return {
        "present": True,
        "label": "Track A ACTIVE (frozen)",
        "global_token_saving_rate": cm.get("global_token_saving_rate"),
        "avg_reconstruction_fidelity_jaccard": cm.get(
            "avg_reconstruction_fidelity_jaccard"
        ),
        "note": "Reference only; beat does not imply promotion or byte_exact on NG path",
    }


def _pareto_label(*, byte_parity: float | None, beat_frozen: bool | None) -> str:
    be = float(byte_parity or 0.0) >= 1.0
    bf = bool(beat_frozen)
    if be and bf:
        return "both_axes_met"
    if be:
        return "byte_exact_only"
    if bf:
        return "semantic_beat_only"
    return "neither"


def _run_py(script: str, extra: list[str]) -> int:
    cmd = [sys.executable, str(ROOT / script), *extra]
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    if cp.stdout.strip():
        print(cp.stdout.strip())
    if cp.stderr.strip():
        print(cp.stderr.strip(), file=sys.stderr)
    return int(cp.returncode)


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _summarize_byte_exact(doc: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for arm in doc.get("arms") or []:
        agg = arm.get("aggregate_metrics") or {}
        rows.append(
            {
                "arm_id": arm.get("arm_label"),
                "lane": "ng40_latent_eval_path",
                "raw": {
                    "byte_exact_subset_parity": arm.get("byte_exact_subset_parity"),
                    "byte_exact_count": arm.get("byte_exact_count"),
                    "case_count": arm.get("case_count"),
                    "global_token_saving_rate": agg.get("global_token_saving_rate"),
                    "avg_reconstruction_fidelity_jaccard": agg.get(
                        "avg_reconstruction_fidelity_jaccard"
                    ),
                },
                "repair_v2": None,
                "delta": {
                    "note": "NG evaluate path; repair_v2 not applied in this harness"
                },
                "pareto_status": _pareto_label(
                    byte_parity=arm.get("byte_exact_subset_parity"),
                    beat_frozen=None,
                ),
            }
        )
    return rows


def _summarize_phase3(doc: dict[str, Any]) -> dict[str, Any]:
    agg = doc.get("aggregate") or {}
    be = doc.get("byte_exact_subset") or {}
    beat = doc.get("beat_check") or {}
    return {
        "arm_id": "phase3_archetype_prior_must_keep",
        "lane": "ng40_latent_eval_path/policy_mask",
        "raw": {
            "byte_exact_subset_parity": be.get("byte_exact_subset_parity"),
            "byte_exact_count": be.get("byte_exact_count"),
            "case_count": be.get("case_count"),
            "global_token_saving_rate": agg.get("global_token_saving_rate"),
            "avg_reconstruction_fidelity_jaccard": agg.get(
                "avg_reconstruction_fidelity_jaccard"
            ),
            "prior_terms_count": doc.get("prior_terms_count"),
        },
        "repair_v2": None,
        "delta": {
            "beat_frozen": beat.get("beat_frozen"),
            "policy_mask_only": doc.get("policy_mask_only"),
        },
        "pareto_status": _pareto_label(
            byte_parity=be.get("byte_exact_subset_parity"),
            beat_frozen=beat.get("beat_frozen"),
        ),
    }


def _summarize_logos_stack(doc: dict[str, Any]) -> dict[str, Any]:
    agg = doc.get("aggregate") or {}
    frozen_note = doc.get("frozen_baseline")
    byte_p = agg.get("byte_exact_subset_parity")
    saving = agg.get("global_token_saving_rate_spine_plus_logos_sidecar") or agg.get(
        "global_token_saving_rate_spine_only"
    )
    j_sem = agg.get("avg_logos_sidecar_jaccard")
    j_spine = agg.get("avg_reconstruction_fidelity_jaccard")
    beat = False
    if frozen_note and isinstance(frozen_note, dict) and frozen_note.get("present"):
        s_f = frozen_note.get("global_token_saving_rate")
        j_f = frozen_note.get("avg_reconstruction_fidelity_jaccard")
        if saving is not None and j_sem is not None and s_f is not None and j_f is not None:
            beat = float(saving) >= float(s_f) and float(j_sem) >= float(j_f)
    return {
        "arm_id": "hybrid_spine_logos_archetype_prior_v1",
        "lane": "hybrid_spine_logos_stack",
        "raw": {
            "byte_exact_subset_parity": byte_p,
            "byte_exact_count": agg.get("byte_exact_count"),
            "case_count": agg.get("case_count"),
            "global_token_saving_rate": saving,
            "avg_reconstruction_fidelity_jaccard": j_spine,
            "avg_logos_sidecar_jaccard": j_sem,
            "salience_hook_wired": doc.get("salience_hook_wired"),
            "logos_terms_count": doc.get("logos_terms_count"),
        },
        "repair_v2": None,
        "delta": {
            "note": "Sidecar Jaccard uses logos/archetype prior terms; recon byte_exact from spine only",
            "semantic_beat_vs_frozen_sidecar_jaccard": beat,
        },
        "pareto_status": _pareto_label(byte_parity=byte_p, beat_frozen=beat),
    }


def _summarize_spine(doc: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for arm in doc.get("arms") or []:
        agg = arm.get("aggregate") or {}
        beat = arm.get("beat_check") or {}
        rows.append(
            {
                "arm_id": arm.get("arm_id"),
                "lane": f"verbatim_spine_bench/{doc.get('mode', 'unknown')}",
                "raw": {
                    "byte_exact_subset_parity": agg.get("byte_exact_subset_parity"),
                    "byte_exact_count": agg.get("byte_exact_count"),
                    "case_count": agg.get("case_count"),
                    "global_token_saving_rate": agg.get("global_token_saving_rate")
                    or agg.get("global_token_saving_rate_spine_plus_sidecar"),
                    "avg_reconstruction_fidelity_jaccard": agg.get(
                        "avg_reconstruction_fidelity_jaccard"
                    ),
                },
                "repair_v2": None,
                "delta": {
                    "beat_frozen": beat.get("beat_frozen"),
                    "delta_saving_pp": beat.get("delta_saving_pp"),
                    "delta_jaccard_pp": beat.get("delta_jaccard_pp"),
                    "reason": beat.get("reason"),
                },
                "pareto_status": _pareto_label(
                    byte_parity=agg.get("byte_exact_subset_parity"),
                    beat_frozen=beat.get("beat_frozen"),
                ),
            }
        )
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=OUT_DEFAULT)
    ap.add_argument(
        "--skip-run",
        action="store_true",
        help="Only merge existing byte_exact + spine JSON (no subprocess)",
    )
    ap.add_argument(
        "--run-hybrid",
        action="store_true",
        help="Also refresh spine bench in hybrid mode (overwrites spine json)",
    )
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    if not args.skip_run:
        rc = _run_py("scripts/run_nextgen_byte_exact_subset_audit_v1.py", [])
        steps.append({"script": "run_nextgen_byte_exact_subset_audit_v1.py", "exit_code": rc})
        if rc != 0:
            return rc
        spine_args = ["--mode", "spine_only"]
        rc2 = _run_py("scripts/run_nextgen_verbatim_spine_bench_v1.py", spine_args)
        steps.append(
            {
                "script": "run_nextgen_verbatim_spine_bench_v1.py",
                "mode": "spine_only",
                "exit_code": rc2,
            }
        )
        if rc2 != 0:
            return rc2
        if args.run_hybrid:
            rc3 = _run_py(
                "scripts/run_nextgen_verbatim_spine_bench_v1.py",
                ["--mode", "hybrid", "--keep-ratio", "0.82"],
            )
            steps.append(
                {
                    "script": "run_nextgen_verbatim_spine_bench_v1.py",
                    "mode": "hybrid",
                    "exit_code": rc3,
                }
            )
            if rc3 != 0:
                return rc3
        rc4 = _run_py("scripts/run_nextgen_hybrid_spine_logos_stack_v1.py", [])
        steps.append(
            {
                "script": "run_nextgen_hybrid_spine_logos_stack_v1.py",
                "exit_code": rc4,
            }
        )
        if rc4 != 0:
            return rc4
        rc5 = _run_py("scripts/run_nextgen_phase3_archetype_prior_chain_v1.py", [])
        steps.append(
            {
                "script": "run_nextgen_phase3_archetype_prior_chain_v1.py",
                "exit_code": rc5,
            }
        )
        if rc5 != 0:
            return rc5

    byte_doc = _load_json(BYTE_EXACT_OUT)
    spine_doc = _load_json(SPINE_OUT)
    logos_stack_doc = _load_json(LOGOS_STACK_OUT)
    phase3_doc = _load_json(PHASE3_OUT)
    hook_doc = _load_json(SALIENCE_HOOK)

    arms_summary: list[dict[str, Any]] = []
    if byte_doc:
        arms_summary.extend(_summarize_byte_exact(byte_doc))
    if spine_doc:
        arms_summary.extend(_summarize_spine(spine_doc))
    if logos_stack_doc:
        logos_stack_doc["frozen_baseline"] = _frozen_baseline()
        arms_summary.append(_summarize_logos_stack(logos_stack_doc))
    if phase3_doc:
        arms_summary.append(_summarize_phase3(phase3_doc))

    both_met = [a for a in arms_summary if a.get("pareto_status") == "both_axes_met"]
    byte_only = [a for a in arms_summary if a.get("pareto_status") == "byte_exact_only"]

    out = {
        "schema": "nextgen_dual_kpi_harness_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "track_a_active_write": False,
        "frozen_baseline": _frozen_baseline(),
        "sources": {
            "byte_exact_subset": _rel(BYTE_EXACT_OUT) if byte_doc else None,
            "verbatim_spine_bench": _rel(SPINE_OUT) if spine_doc else None,
            "hybrid_spine_logos_stack": _rel(LOGOS_STACK_OUT) if logos_stack_doc else None,
            "phase3_archetype_prior_mask": _rel(PHASE3_OUT) if phase3_doc else None,
            "salience_hook": _rel(SALIENCE_HOOK) if hook_doc else None,
            "nav_frame": _rel(NAV_FRAME) if NAV_FRAME.is_file() else None,
        },
        "arms_summary": arms_summary,
        "pareto_synthesis": {
            "both_axes_met_arms": [a["arm_id"] for a in both_met],
            "byte_exact_only_arms": [a["arm_id"] for a in byte_only],
            "simultaneous_byte_and_active_beat": len(both_met) > 0,
            "status": "TBD"
            if not both_met
            else "partial_single_arm",
            "note_ko": "양축 동시 만족 arm 없으면 TBD; spine_only는 byte만, ng40_latent는 semantic만인 경우가 일반적",
        },
        "reporting": {
            "raw_primary": True,
            "repair_v2": None,
            "never_collapse_headline": True,
        },
        "guardrails": [
            "Does not write MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT",
            "Does not merge general_prophecy L1 with NG codec",
            "B→A and live trading auto-merge forbidden",
        ],
        "subprocess_steps": steps,
        "stub_pointer": (
            "experiments/nextgen_clean_slate_cpu_v1/"
            "SYMBOLIC_ARCHETYPE_PREDICTIVE_INDEX_STUB_V1.json"
        ),
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "wrote": str(args.out_json),
                "arm_count": len(arms_summary),
                "both_axes_met": len(both_met),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
