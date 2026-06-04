#!/usr/bin/env python3
"""Materialize [HYPO] next-gen corpus indexer charter (parallel arms vs Golden-40 frozen)."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports/btrack_nextgen_indexer_charter_v1_latest.json"
SCHEMA = ROOT / "docs/final/schemas/btrack_nextgen_indexer_charter_v1.schema.json"
ACTIVE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
BENCH_INPUT = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p.resolve()).replace("\\", "/")


def _exists(rel: str) -> bool:
    return (ROOT / rel.replace("/", "\\")).is_file() or (ROOT / rel).is_file()


def _frozen_metrics() -> dict:
    metrics: dict = {
        "global_token_saving_rate": None,
        "avg_reconstruction_fidelity_jaccard": None,
        "alignment_pass_rate_raw": None,
        "alignment_pass_rate_repair_v2": None,
    }
    if not ACTIVE.is_file():
        return metrics
    doc = json.loads(ACTIVE.read_text(encoding="utf-8"))
    cm = doc.get("compression_metrics") or {}
    metrics["global_token_saving_rate"] = cm.get("global_token_saving_rate")
    metrics["avg_reconstruction_fidelity_jaccard"] = cm.get(
        "avg_reconstruction_fidelity_jaccard"
    )
    for key, out_key in (
        ("alignment_pass_rate_raw", "alignment_pass_rate_raw"),
        ("alignment_pass_rate", "alignment_pass_rate_repair_v2"),
        ("alignment_pass_rate_repair_v2", "alignment_pass_rate_repair_v2"),
    ):
        if cm.get(key) is not None:
            metrics[out_key] = cm.get(key)
    return metrics


def main() -> int:
    frozen = _frozen_metrics()
    saving = frozen.get("global_token_saving_rate")
    jacc = frozen.get("avg_reconstruction_fidelity_jaccard")
    headline = "47.5% saving · Jaccard ~0.89 (frozen Track A; round for external only)"
    if saving is not None and jacc is not None:
        headline = (
            f"{round(saving * 100, 1)}% saving · Jaccard ~{round(jacc, 3)} "
            "(snapshot from active report; external round only)"
        )

    doc: dict = {
        "schema": "btrack_nextgen_indexer_charter_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "track_a_active_write": False,
        "hypo_label": "[HYPO]",
        "branch_name": "feature/btrack-nextgen-indexer-v1",
        "one_page_summary_ko": (
            "31k/41k 패치워크를 한 번에 폐기하지 않는다. 동일 Golden-40 벤치에서 "
            "legacy 41k·GPU semantic·[HYPO] latent indexer 3-arm 병렬 측정 후 beat+서명 시에만 은퇴."
        ),
        "paradigm_shift_summary_ko": (
            "궁극 목표는 discrete lookup+별도 벡터 지도를 연속 잠재공간·코퍼스 내재화로 대체하는 것이나, "
            "운영 본선은 TRACK_A_STRICT_LOCK 동안 frozen baseline을 유지한다."
        ),
        "constitution_meta": {
            "route_setting": "선로 ① 고정 / ② 패시브",
            "track_a_strict_lock": True,
            "fail_comp_004_summary": (
                "repair-only·1103·nextgen uplift를 Track A·live·MS 헤드라인에 자동 합선 금지"
            ),
            "mission_log_section": "MISSION_LOG.md §작전 지휘선 · Next-Gen indexer",
            "supersedes_local_optimization_only": True,
        },
        "parallel_bench_arms": [
            {
                "arm_id": "legacy_discrete_41k",
                "label_ko": "동결 Track A — 41k lookup + 4D policy OFF",
                "implementation_status": "frozen_production_ssot",
                "same_bench_cases": _rel(BENCH_INPUT),
                "metrics_required": [
                    "global_token_saving_rate",
                    "avg_reconstruction_fidelity_jaccard",
                    "alignment_pass_rate_raw",
                ],
                "script_pointers": [
                    _rel(ROOT / "scripts/run_ultra_compression_default.py"),
                    _rel(ROOT / "scripts/comp_atom02_lexicon_must_keep_analysis_v1.py"),
                ],
                "artifact_pointers": [
                    _rel(ACTIVE),
                    _rel(BENCH_INPUT),
                ],
                "reporting": "raw primary; repair_v2 operational if repair layer used",
            },
            {
                "arm_id": "gpu_semantic_poc",
                "label_ko": "GPU semantic PoC (en_tech zone; 41k 대체 아님)",
                "implementation_status": "partial_poc",
                "same_bench_cases": _rel(BENCH_INPUT),
                "metrics_required": [
                    "global_token_saving_rate",
                    "avg_reconstruction_fidelity_jaccard",
                ],
                "script_pointers": [
                    _rel(ROOT / "scripts/run_en_tech_semantic_gpu_poc_v1.py"),
                    _rel(ROOT / "scripts/Run-MkmGpuRecommendedBundle_v1.ps1"),
                ],
                "artifact_pointers": [
                    _rel(
                        ROOT
                        / "reports/constitution/btrack_pilot/comp_en_tech_semantic_gpu_poc_local_v1_latest.json"
                    ),
                ],
                "reporting": "raw vs repair_v2 delta required when repair touched",
            },
            {
                "arm_id": "nextgen_latent_indexer",
                "label_ko": "[HYPO] Native neural corpus indexer — CPU clean-slate distributed PoC",
                "implementation_status": "partial_poc",
                "same_bench_cases": _rel(BENCH_INPUT),
                "metrics_required": [
                    "global_token_saving_rate",
                    "avg_reconstruction_fidelity_jaccard",
                    "alignment_pass_rate_raw",
                ],
                "script_pointers": [
                    _rel(ROOT / "scripts/run_nextgen_clean_slate_cpu_sandbox_chain_v1.py"),
                    _rel(ROOT / "scripts/Run-NextGenCleanSlateCpuSandbox_v1.ps1"),
                    _rel(ROOT / "scripts/run_btrack_nextgen_indexer_parallel_bench_chain_v1.py"),
                ],
                "artifact_pointers": [
                    _rel(
                        ROOT
                        / "experiments/nextgen_clean_slate_cpu_v1/results/nextgen_neural_baseline_v1_latest.json"
                    ),
                    _rel(ROOT / "reports/btrack_nextgen_indexer_parallel_bench_v1_latest.json"),
                ],
                "reporting": (
                    "nextgen_neural_baseline_v1 (Golden-40 incompatible); "
                    "NG-40 shadow when P2 latent stub exists"
                ),
            },
        ],
        "frozen_baseline": {
            "bench_input": _rel(BENCH_INPUT),
            "active_report": _rel(ACTIVE),
            "headline_rounded": headline,
            "metrics_snapshot": frozen,
        },
        "retire_gates": {
            "legacy_41k_disconnect_allowed": False,
            "conditions_all_required": [
                "nextgen or gpu arm beats frozen Golden-40 on same 40-case bench (JSON evidence)",
                "raw alignment_pass_rate meets promotion gate where applicable",
                "human_signoff on MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json",
                "TRACK_A_STRICT_LOCK explicitly released by commander order",
            ],
            "new_baseline_ssot_after_beat": _rel(
                ROOT / "reports/btrack_nextgen_indexer_parallel_bench_v1_latest.json"
            ),
        },
        "related_specs": [
            _rel(ROOT / "reports/mkm_gpu_hybrid_transition_spec_v1_latest.json"),
            _rel(
                ROOT
                / "docs/final/artifacts/btrack_31k41k_prophecy_shadow_experiment_spec_v1_latest.md"
            ),
            _rel(ROOT / "experiments/nextgen_clean_slate_cpu_v1/README.md"),
            _rel(
                ROOT
                / "docs/final/schemas/nextgen_clean_slate_cpu_topology_v1.schema.json"
            ),
        ],
        "forbidden": [
            "delete 41k lexicon or 31k verse SSOT before parallel beat + human sign-off",
            "overwrite MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json from charter or PoC",
            "single pipeline merging compression, prophecy shadow, and nextgen indexer",
            "promote Track A·live·MS from repair_v2 or charter-only uplift",
            "declare Jaccard loss eliminated without measured NG-40 shadow bench",
        ],
        "dod_exit_criteria": [
            {
                "criterion_id": "DOD-CHARTER",
                "description": "Charter JSON materialized and validates against schema",
                "commands_optional": [
                    "py scripts/build_btrack_nextgen_indexer_charter_v1.py",
                ],
                "evidence_paths": [_rel(OUT)],
                "human_signoff_required": False,
            },
            {
                "criterion_id": "DOD-PARALLEL-BENCH-PLAN",
                "description": "Parallel bench chain emits plan or summary with 3-arm status",
                "commands_optional": [
                    "py scripts/run_btrack_nextgen_indexer_parallel_bench_chain_v1.py --dry-run",
                ],
                "evidence_paths": [
                    _rel(ROOT / "reports/btrack_nextgen_indexer_parallel_bench_v1_latest.json"),
                ],
                "human_signoff_required": False,
            },
            {
                "criterion_id": "DOD-BEAT-FROZEN",
                "description": "Candidate arm beats frozen baseline on same bench; human sign-off",
                "commands_optional": [
                    "py scripts/run_btrack_nextgen_indexer_parallel_bench_chain_v1.py --execute",
                ],
                "evidence_paths": [_rel(OUT)],
                "human_signoff_required": True,
            },
        ],
        "guardrails": [
            "Charter is B-track [HYPO] planning SSOT; CONSTITUTION + scripts remain implementation facts",
            "Golden-40 frozen metrics are parallel reference, not retired by this file alone",
            "31k corpus text SSOT retire forbidden; ANN/embedding layers additive only",
        ],
    }

    missing = [
        p
        for block in doc["dod_exit_criteria"]
        for p in block.get("evidence_paths", [])
        if p and not _exists(p)
    ]
    doc["path_check"] = {
        "dod_evidence_all_present": len(missing) == 0,
        "missing_optional_note": missing[:12],
        "active_report_present": ACTIVE.is_file(),
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "wrote": str(OUT),
                "schema": _rel(SCHEMA),
                "missing_count": len(missing),
                "headline": headline,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
