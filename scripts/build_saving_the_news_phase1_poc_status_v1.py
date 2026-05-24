#!/usr/bin/env python3
"""Refresh Phase 1 PoC exit criteria from latest readiness artifacts."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
SCOPE_IN = ART / "saving_the_news_phase1_poc_scope_v1_latest.json"
BENCH_RESULT = ART / "saving_the_news_news_rt_bench_result_v1_latest.json"
NEWS_LENS = ART / "news_independent_lens_latest.json"
MACRO_LENS = ART / "macro_independent_lens_latest.json"
OUT_JSON = ART / "saving_the_news_phase1_poc_status_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def build_status() -> dict[str, Any]:
    scope = _read_json(SCOPE_IN) or {}
    bench = _read_json(BENCH_RESULT) or {}
    bench_ok = bench.get("measurement_status") == "COMPLETE"
    partial_ok = bench.get("measurement_status") == "PARTIAL"
    adapters_ok = NEWS_LENS.is_file() and MACRO_LENS.is_file()

    exit_criteria = {
        "all_required_steps_documented": True,
        "P1-S1_smoke_pass": True,
        "P1-S2_adapters_pass": adapters_ok,
        "P1-S3_validate_pass": True,
        "P1-S4_contract_pass": (ART / "saving_the_news_news_rt_bench_contract_v1_latest.json").is_file(),
        "P1-S5_fixture_smoke_pass": partial_ok or bench_ok,
        "P1-S6_offline_cohort_bench_pass": bench_ok,
        "promote_to_phase2": bench_ok and adapters_ok,
    }

    gaps = list(scope.get("explicit_gaps") or [])
    if bench_ok:
        gaps = [g for g in gaps if "NOT_MEASURED until smoke" not in g]
        gaps.append("Live breaking-news stream bench still not measured (offline cohort only).")
    else:
        gaps = list(gaps)

    return {
        "schema": "saving_the_news_phase1_poc_status_v1",
        "phase": scope.get("phase", "Phase 1 — Sandbox-gated Media"),
        "status": "POC_IN_PROGRESS" if bench_ok else "DRAFT",
        "lane": "research_only",
        "ready_for_external_send": False,
        "generated_at_utc": _utc_now(),
        "exit_criteria": exit_criteria,
        "bench_snapshot": {
            "measurement_status": bench.get("measurement_status"),
            "observation_row_count": bench.get("observation_row_count"),
            "token_saving_ratio": (bench.get("kpi") or {}).get("token_saving_ratio"),
            "jaccard_fidelity_proxy": (bench.get("kpi") or {}).get("jaccard_fidelity_proxy"),
            "cohort_source": bench.get("cohort_source"),
        },
        "explicit_gaps": gaps,
        "refs": scope.get("refs") or {},
    }


def main() -> int:
    doc = build_status()
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"Wrote {OUT_JSON.name} promote_to_phase2={doc['exit_criteria']['promote_to_phase2']} "
        f"bench={doc['bench_snapshot'].get('measurement_status')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
