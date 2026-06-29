#!/usr/bin/env python3
"""W1-1 Finance-axis hypo status — separate from main NEWS-RT / phase1 SSOT."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BENCH = ROOT / "docs/final/artifacts/saving_the_news_news_rt_bench_result_finance_hypo_v1_latest.json"
DEFAULT_COHORT = ROOT / "docs/final/artifacts/news_observation_v1_finance_hypo_latest.jsonl"
DEFAULT_OUT = ROOT / "docs/final/artifacts/saving_the_news_finance_hypo_status_v1_latest.json"
JACCARD_GO_FLOOR = 0.50


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def build_status(bench: dict[str, Any], *, cohort_path: Path, jaccard_floor: float) -> dict[str, Any]:
    kpi = bench.get("kpi") if isinstance(bench.get("kpi"), dict) else {}
    jaccard = kpi.get("jaccard_fidelity_proxy")
    measured = bench.get("measurement_status") == "COMPLETE"
    second_axis_go = (
        measured
        and isinstance(jaccard, (int, float))
        and float(jaccard) >= jaccard_floor
    )
    return {
        "schema": "saving_the_news_finance_hypo_status_v1",
        "generated_at_utc": _utc_now(),
        "lane": "research_only",
        "hypothesis_tag": "[HYPO]",
        "axis_id": "finance_hypo",
        "ready_for_external_send": False,
        "promote_to_deck": False,
        "promote_to_portal": False,
        "measurement_status": bench.get("measurement_status"),
        "second_axis_go": second_axis_go,
        "jaccard_go_floor": jaccard_floor,
        "kpi": {
            "token_saving_ratio": kpi.get("token_saving_ratio"),
            "jaccard_fidelity_proxy": jaccard,
            "integrity_score": kpi.get("integrity_score"),
            "observation_row_count": bench.get("observation_row_count"),
        },
        "go_no_go": {
            "verdict": "GO_SECOND_AXIS_PILOT" if second_axis_go else "HOLD_SECOND_AXIS",
            "reason_ko": (
                f"Finance 오프라인 코호트 Jaccard {float(jaccard):.4f} >= {jaccard_floor}"
                if second_axis_go and isinstance(jaccard, (int, float))
                else (
                    f"벤치 미완료 또는 Jaccard < {jaccard_floor} — IT 축·덱 반영 보류"
                    if not second_axis_go
                    else "벤치 완료, Go 판정"
                )
            ),
        },
        "explicit_gaps": [
            "Not merged into news_observation_v1_latest.jsonl",
            "Not live breaking-news stream bench",
            "No second RSS axis (IT) until finance hypo Go",
        ],
        "refs": {
            "cohort_jsonl": _rel(cohort_path) if cohort_path.is_file() else None,
            "bench_result": _rel(DEFAULT_BENCH) if DEFAULT_BENCH.is_file() else None,
            "main_news_rt_bench": "docs/final/artifacts/saving_the_news_news_rt_bench_result_v1_latest.json",
            "rss_sources": "data/mkmlife/rss_sources_finance_hypo_v1.json",
        },
        "forbidden": [
            "Do not cite finance_hypo KPI as main NEWS-RT proof",
            "Do not auto-merge into mkmlife deck or Track A",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Finance hypo W1-1 status JSON")
    ap.add_argument("--bench-json", type=Path, default=DEFAULT_BENCH)
    ap.add_argument("--cohort-jsonl", type=Path, default=DEFAULT_COHORT)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--jaccard-go-floor", type=float, default=JACCARD_GO_FLOOR)
    args = ap.parse_args()

    bench_path = args.bench_json.resolve()
    if not bench_path.is_file():
        raise SystemExit(f"missing bench: {bench_path}")
    bench = json.loads(bench_path.read_text(encoding="utf-8-sig"))
    doc = build_status(bench, cohort_path=args.cohort_jsonl.resolve(), jaccard_floor=args.jaccard_go_floor)
    out = args.output_json.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "output_json": _rel(out),
                "second_axis_go": doc["second_axis_go"],
                "verdict": doc["go_no_go"]["verdict"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
