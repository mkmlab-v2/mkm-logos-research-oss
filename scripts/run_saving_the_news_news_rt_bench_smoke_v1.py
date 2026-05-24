#!/usr/bin/env python3
"""NEWS-RT PoC smoke — fixture-only partial metrics (not live stream)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
OUT_JSON = ART / "saving_the_news_news_rt_bench_result_v1_latest.json"
FIXTURE_NEWS = ROOT / "tests/fixtures/news_observation_v1.sample.jsonl"
CONTRACT = ART / "saving_the_news_news_rt_bench_contract_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _count_jsonl(path: Path) -> int:
    if not path.is_file():
        return 0
    n = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            n += 1
    return n


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def run_smoke() -> dict[str, Any]:
    n_rows = _count_jsonl(FIXTURE_NEWS)
    min_required = 1
    contract_ok = CONTRACT.is_file()
    # Placeholder partial metrics — fixture cohort only, not comparable to A-TRACK/LOGOS-CAP.
    partial_ok = contract_ok and n_rows >= min_required
    return {
        "schema": "saving_the_news_news_rt_bench_result_v1",
        "axis_id": "NEWS-RT",
        "lane": "research_only",
        "generated_at_utc": _utc_now(),
        "cohort_id": "fixture_news_observation_v1_sample",
        "cohort_source": _display_path(FIXTURE_NEWS),
        "observation_row_count": n_rows,
        "measurement_status": "PARTIAL" if partial_ok else "NOT_MEASURED",
        "status": "POC_SMOKE_FIXTURE_ONLY",
        "ready_for_external_send": False,
        "kpi": {
            "token_saving_ratio": None,
            "jaccard_fidelity_proxy": None,
            "integrity_score": 1.0 if partial_ok else None,
            "latency_p99_ms": None,
            "notes": "Fixture smoke only. No compression bench run on live news stream.",
        },
        "forbidden_interpretation": [
            "Not A-TRACK 47.5% or LOGOS-CAP 84.5% transfer.",
            "Not READY_FOR_NEWS_CLAIMS from news_benchmark_readiness.",
        ],
        "contract_ref": _display_path(CONTRACT) if contract_ok else None,
    }


def main() -> int:
    doc = run_smoke()
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"Wrote {_display_path(OUT_JSON)} "
        f"measurement_status={doc['measurement_status']} rows={doc['observation_row_count']}"
    )
    return 0 if doc["measurement_status"] != "NOT_MEASURED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
