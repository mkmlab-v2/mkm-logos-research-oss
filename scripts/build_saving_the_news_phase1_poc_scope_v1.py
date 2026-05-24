#!/usr/bin/env python3
"""Phase 1 Sandbox-gated Media PoC scope manifest (Saving the News)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
OUT_JSON = ART / "saving_the_news_phase1_poc_scope_v1_latest.json"
NEWS_RT_CONTRACT = ART / "saving_the_news_news_rt_bench_contract_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _exists(rel: str) -> bool:
    return (ROOT / rel.replace("/", "\\")).is_file() if "\\" in str(ROOT) else (ROOT / rel).is_file()


def build_scope(*, news_rt_contract_exists: bool | None = None) -> dict[str, Any]:
    if news_rt_contract_exists is None:
        news_rt_contract_exists = NEWS_RT_CONTRACT.is_file()

    steps = [
        {
            "id": "P1-S1",
            "title": "Observation contract smoke",
            "script": "scripts/Run-NewsObservationContractSmoke.ps1",
            "pass_criterion": "exit 0",
            "network_required": False,
        },
        {
            "id": "P1-S2",
            "title": "News/macro lens adapters",
            "script": "scripts/build_btrack_news_macro_lens_adapters_v1.py",
            "pass_criterion": "news_independent_lens_latest.json + macro_independent_lens_latest.json refreshed",
            "network_required": False,
        },
        {
            "id": "P1-S3",
            "title": "Pre-send schema gate (offline)",
            "script": "scripts/validate_news_observation_jsonl_v1.py",
            "pass_criterion": "fixture jsonl validates with --verify-label-hashes",
            "network_required": False,
            "note": "Production CMS Lock [HYPO] — not shipped",
        },
        {
            "id": "P1-S4",
            "title": "NEWS-RT contract frozen",
            "script": "scripts/build_saving_the_news_news_rt_bench_contract_v1.py",
            "pass_criterion": "saving_the_news_news_rt_bench_contract_v1_latest.json exists",
            "network_required": False,
        },
        {
            "id": "P1-S5",
            "title": "NEWS-RT fixture bench smoke",
            "script": "scripts/run_saving_the_news_news_rt_bench_smoke_v1.py",
            "pass_criterion": "measurement_status PARTIAL on fixture cohort only",
            "network_required": False,
            "optional": True,
        },
        {
            "id": "P1-S6",
            "title": "NEWS-RT offline cohort bench (>=120 rows)",
            "script": "scripts/Run-SavingTheNewsNewsRtBench_v1.ps1",
            "pass_criterion": "saving_the_news_news_rt_bench_result_v1_latest.json measurement_status COMPLETE",
            "network_required": False,
        },
    ]

    gates = {
        "schema_validation": _exists("docs/final/schemas/news_observation_v1.schema.json"),
        "news_rt_contract": news_rt_contract_exists,
        "adapters_artifacts": _exists("docs/final/artifacts/news_independent_lens_latest.json"),
        "cms_publish_lock_product": False,
        "zero_hallucination_claim": False,
        "ready_for_external_send": False,
    }

    return {
        "schema": "saving_the_news_phase1_poc_scope_v1",
        "phase": "Phase 1 — Sandbox-gated Media",
        "status": "DRAFT",
        "lane": "research_only",
        "hypothesis_tier": "B",
        "ready_for_external_send": False,
        "generated_at_utc": _utc_now(),
        "objective_ko": "작성·송출 전 원천·스키마·오프라인 일치 스캔 [HYPO] — CMS Lock 미구현",
        "steps": steps,
        "gates": gates,
        "exit_criteria": {
            "all_required_steps_documented": True,
            "P1-S1_smoke_pass": None,
            "P1-S2_adapters_pass": None,
            "P1-S4_contract_pass": news_rt_contract_exists,
            "promote_to_phase2": False,
        },
        "explicit_gaps": [
            "Real-time CMS publish lock",
            "NEWS-RT live-stream cohort bench (NOT_MEASURED until smoke records PARTIAL+)",
            "95% trust mark / cryptographic shield",
        ],
        "refs": {
            "blueprint": "docs/research/saving_the_news_blueprint_v1.md",
            "news_rt_contract": "docs/final/artifacts/saving_the_news_news_rt_bench_contract_v1_latest.json",
            "track_c_onepager": "docs/final/artifacts/track_c_saving_the_news_offer_onepager_v1_latest.md",
        },
    }


def main() -> int:
    doc = build_scope()
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT_JSON.relative_to(ROOT)} gates.news_rt_contract={doc['gates']['news_rt_contract']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
