#!/usr/bin/env python3
"""Emit NEWS-RT bench contract (design-only until explicit bench run)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
OUT_JSON = ART / "saving_the_news_news_rt_bench_contract_v1_latest.json"

FORBIDDEN = [
    "Do not cite A-TRACK ~47.5% saving as NEWS-RT proof.",
    "Do not cite LOGOS-CAP 84.5% saving as NEWS-RT proof.",
    "Do not claim live news stream bench complete while measurement_status is NOT_MEASURED.",
    "Do not claim token↔latency causal link (RQ-017).",
]

PREREQ_PATHS = {
    "news_observation_schema": "docs/final/schemas/news_observation_v1.schema.json",
    "pre_news_shadow_input": "docs/final/artifacts/pre_news_shadow_input_latest.json",
    "news_independent_lens": "docs/final/artifacts/news_independent_lens_latest.json",
    "macro_independent_lens": "docs/final/artifacts/macro_independent_lens_latest.json",
    "news_benchmark_readiness": "docs/final/artifacts/news_benchmark_readiness_latest.json",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_contract(*, prerequisite_checks: dict[str, Any] | None = None) -> dict[str, Any]:
    checks = prerequisite_checks or {}
    if not checks:
        for key, rel in PREREQ_PATHS.items():
            p = ROOT / rel.replace("/", "\\") if "\\" in str(ROOT) else ROOT / rel
            checks[key] = {"path": rel.replace("\\", "/"), "exists": p.is_file()}

    return {
        "schema": "saving_the_news_news_rt_bench_contract_v1",
        "axis_id": "NEWS-RT",
        "status": "DESIGN_ONLY",
        "lane": "research_only",
        "hypothesis_tier": "B",
        "ready_for_external_send": False,
        "generated_at_utc": _utc_now(),
        "measurement_status": "NOT_MEASURED",
        "forbidden_cross_axis_claims": FORBIDDEN,
        "input_contracts": {
            "news_observation_schema": "news_observation_v1",
            "min_observation_rows": 120,
            "point_in_time_required": True,
            "pre_news_shadow_input": PREREQ_PATHS["pre_news_shadow_input"],
            "news_independent_lens": PREREQ_PATHS["news_independent_lens"],
            "macro_independent_lens": PREREQ_PATHS["macro_independent_lens"],
        },
        "kpi_slots": {
            "token_saving_ratio": None,
            "jaccard_fidelity_proxy": None,
            "integrity_score": None,
            "latency_p99_ms": None,
            "measured_at_utc": None,
            "cohort_id": None,
            "notes": "Populate only after run_saving_the_news_news_rt_bench_smoke_v1 records a cohort.",
        },
        "bench_chain_scripts": [
            {
                "order": 1,
                "script": "scripts/Run-NewsObservationContractSmoke.ps1",
                "purpose": "news_observation_v1 schema + join guards",
            },
            {
                "order": 2,
                "script": "scripts/build_btrack_news_macro_lens_adapters_v1.py",
                "purpose": "news/macro independent lens slots for B-track bundle",
            },
            {
                "order": 3,
                "script": "scripts/run_pre_news_shadow_ops_smoke_v1.py",
                "purpose": "Pre-News shadow ops contract (optional network-free paths)",
                "optional": True,
            },
            {
                "order": 4,
                "script": "scripts/run_saving_the_news_news_rt_bench_smoke_v1.py",
                "purpose": "NEWS-RT PoC smoke — records PARTIAL metrics only on fixture cohort",
                "optional": True,
            },
            {
                "order": 5,
                "script": "scripts/run_saving_the_news_news_rt_bench_v1.py",
                "purpose": "NEWS-RT offline cohort bench (default news_observation_v1_latest.jsonl)",
            },
            {
                "order": 6,
                "script": "scripts/build_saving_the_news_phase1_poc_status_v1.py",
                "purpose": "Phase 1 exit criteria snapshot",
            },
        ],
        "artifact_outputs": {
            "bench_result_latest": "docs/final/artifacts/saving_the_news_news_rt_bench_result_v1_latest.json",
            "readiness_pointer": "docs/final/artifacts/news_benchmark_readiness_latest.json",
        },
        "blueprint_refs": {
            "canonical_blueprint": "docs/research/saving_the_news_blueprint_v1.md",
            "track_c_onepager": "docs/final/artifacts/track_c_saving_the_news_offer_onepager_v1_latest.md",
            "rq_ids": ["RQ-011", "RQ-022"],
        },
        "prerequisite_checks": checks,
    }


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def main() -> int:
    doc = build_contract()
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {_display_path(OUT_JSON)} measurement_status={doc['measurement_status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
