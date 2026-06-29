#!/usr/bin/env python3
"""NEWS-HP-RT offline bench — priors-weighted compression vs NEWS-RT baseline [HYPO]."""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
ART = ROOT / "docs" / "final" / "artifacts"
OUT_JSON = ART / "saving_the_news_news_hp_rt_bench_result_v1_latest.json"
DEFAULT_COHORT = ART / "news_observation_v1_latest.jsonl"
DEFAULT_INTAKE = ART / "hyper_personal_news_intake_v1_latest.json"

from scripts.run_saving_the_news_news_rt_bench_v1 import (  # noqa: E402
    MIN_ROWS_DEFAULT,
    _load_cohort,
    _jaccard,
    _token_count,
    compress_state_card_v0,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def _effective_char_ratio(base_ratio: float, priors: dict[str, float]) -> float:
    sasang = float(priors.get("sasang_scalar") or 0.5)
    myeongni = abs(float(priors.get("myeongni_day_pillar_prior_hypo") or 0.0))
    wellness = float(priors.get("wellness_hypo_budget") or 0.25)
    tuned = base_ratio * (1.0 - 0.12 * sasang - 0.05 * myeongni - 0.03 * wellness)
    return max(0.25, min(0.85, tuned))


def run_hp_bench(
    cohort_path: Path,
    priors: dict[str, float],
    *,
    min_rows: int = MIN_ROWS_DEFAULT,
    base_char_ratio: float = 0.55,
) -> dict[str, Any]:
    rows = _load_cohort(cohort_path)
    n = len(rows)
    if n < min_rows:
        return {
            "schema": "saving_the_news_news_hp_rt_bench_result_v1",
            "axis_id": "NEWS-HP-RT",
            "lane": "research_only",
            "hypothesis_tier": "B",
            "generated_at_utc": _utc_now(),
            "observation_row_count": n,
            "min_rows_required": min_rows,
            "measurement_status": "NOT_MEASURED",
            "status": "COHORT_TOO_SMALL",
            "ready_for_external_send": False,
            "priors_applied": priors,
            "kpi": None,
            "delta_vs_news_rt_baseline": None,
            "forbidden_interpretation": _forbidden(),
        }

    base_ratio = base_char_ratio
    hp_ratio = _effective_char_ratio(base_ratio, priors)
    base_savings: list[float] = []
    hp_savings: list[float] = []
    base_j: list[float] = []
    hp_j: list[float] = []

    for row in rows:
        raw = str(row.get("canonical_text", ""))
        base_c = compress_state_card_v0(raw, target_char_ratio=base_ratio)
        hp_c = compress_state_card_v0(raw, target_char_ratio=hp_ratio)
        rt = _token_count(raw)
        base_savings.append(1.0 - (_token_count(base_c) / rt if rt else 0.0))
        hp_savings.append(1.0 - (_token_count(hp_c) / rt if rt else 0.0))
        base_j.append(_jaccard(raw, base_c))
        hp_j.append(_jaccard(raw, hp_c))

    base_mean = statistics.mean(base_savings)
    hp_mean = statistics.mean(hp_savings)
    return {
        "schema": "saving_the_news_news_hp_rt_bench_result_v1",
        "axis_id": "NEWS-HP-RT",
        "lane": "research_only",
        "hypothesis_tier": "B",
        "generated_at_utc": _utc_now(),
        "cohort_id": cohort_path.stem,
        "cohort_source": _rel(cohort_path),
        "observation_row_count": n,
        "min_rows_required": min_rows,
        "measurement_status": "COMPLETE",
        "status": "OFFLINE_COHORT_BENCH_PRIORS_WEIGHTED",
        "ready_for_external_send": False,
        "compression_method": "state_card_unique_token_v0_priors_tuned",
        "compression_params": {
            "baseline_target_char_ratio": base_ratio,
            "hp_target_char_ratio": round(hp_ratio, 6),
        },
        "priors_applied": priors,
        "kpi": {
            "token_saving_ratio_baseline_news_rt": round(base_mean, 6),
            "token_saving_ratio_hp_weighted": round(hp_mean, 6),
            "jaccard_fidelity_proxy_baseline": round(statistics.mean(base_j), 6),
            "jaccard_fidelity_proxy_hp_weighted": round(statistics.mean(hp_j), 6),
            "notes": (
                "Offline cohort with §10 priors tuning stub only. "
                "Not live stream. Not promotion proof for Track A or CMS."
            ),
        },
        "delta_vs_news_rt_baseline": {
            "token_saving_ratio_delta_hp_minus_baseline": round(hp_mean - base_mean, 6),
            "interpretation": "research_only_delta",
        },
        "forbidden_interpretation": _forbidden(),
    }


def _forbidden() -> list[str]:
    return [
        "Not A-TRACK 47.5% or LOGOS-CAP 84.5% transfer.",
        "Not consumer app readiness or CMS publish approval.",
        "Priors do not override news ranking alone — shadow weight tuning only.",
        "Not live breaking-news stream latency proof.",
    ]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cohort-jsonl", type=Path, default=DEFAULT_COHORT)
    ap.add_argument("--intake-json", type=Path, default=DEFAULT_INTAKE)
    ap.add_argument("--min-rows", type=int, default=MIN_ROWS_DEFAULT)
    ap.add_argument("--base-char-ratio", type=float, default=0.55)
    ap.add_argument("--out-json", type=Path, default=OUT_JSON)
    args = ap.parse_args()

    intake = {}
    if args.intake_json.is_file():
        intake = json.loads(args.intake_json.read_text(encoding="utf-8"))
    priors = (intake.get("field") or {}).get("priors") or {
        "sasang_scalar": 0.5,
        "myeongni_day_pillar_prior_hypo": 0.0,
        "wellness_hypo_budget": 0.25,
    }

    doc = run_hp_bench(
        args.cohort_jsonl,
        priors,
        min_rows=args.min_rows,
        base_char_ratio=args.base_char_ratio,
    )
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"WROTE: {args.out_json} status={doc.get('measurement_status')} "
        f"rows={doc.get('observation_row_count')}"
    )
    return 0 if doc.get("measurement_status") == "COMPLETE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
