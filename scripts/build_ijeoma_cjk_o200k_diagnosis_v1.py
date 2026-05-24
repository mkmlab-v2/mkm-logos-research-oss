#!/usr/bin/env python3
"""[HYPO] Diagnose proxy vs o200k_base token counts for CJK substitution (B-track)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.comp_graphrag_philosophy_compression_sweep_v1 import BASE_MUST_KEEP  # noqa: E402
from scripts.ijeoma_cjk_compression_hypo_v1 import (  # noqa: E402
    compress_ijeoma_cjk_substitution,
    default_hypo_lexicon_path,
)
from scripts.report_multilens_performance_eval import (  # noqa: E402
    _o200k_saving_rate,
    _tiktoken_o200k_status,
    evaluate_report,
)

LANE = ROOT / "docs/final/artifacts/universal_compression_bench_lane_ijeoma_chunk_table_v1.json"
OUT_PUA = ROOT / "reports/constitution/btrack_pilot/comp_ijeoma_cjk_o200k_diagnosis_v1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lane-json", type=Path, default=LANE)
    ap.add_argument("--lexicon-json", type=Path, default=None)
    ap.add_argument("--max-cases", type=int, default=0)
    ap.add_argument("--out-json", type=Path, default=None)
    ap.add_argument(
        "--marker-strategy",
        choices=("pua", "ascii_compact", "atom_id", "o200k_tight"),
        default="pua",
    )
    args = ap.parse_args()

    enc, err = _tiktoken_o200k_status()
    if enc is None:
        print(json.dumps({"error": "tiktoken_unavailable", "reason": err}, ensure_ascii=False))
        return 2

    lane_path = (ROOT / args.lane_json).resolve() if not args.lane_json.is_absolute() else args.lane_json
    lex_path = (
        Path(args.lexicon_json).resolve()
        if args.lexicon_json
        else default_hypo_lexicon_path()
    )
    if args.out_json:
        out_path = (ROOT / args.out_json).resolve() if not args.out_json.is_absolute() else args.out_json
    elif args.marker_strategy == "pua":
        out_path = OUT_PUA
    else:
        out_path = ROOT / f"reports/constitution/btrack_pilot/comp_ijeoma_cjk_o200k_diagnosis_{args.marker_strategy}_v1.json"

    cases = json.loads(lane_path.read_text(encoding="utf-8")).get("compression_cases") or []
    if args.max_cases > 0:
        cases = cases[: args.max_cases]

    rows: list[dict[str, Any]] = []
    sum_raw_o2 = sum_comp_o2 = 0
    per_case_rates: list[float] = []
    proxy_rates: list[float] = []
    negative_o2_cases = 0

    for case in cases:
        raw = str(case.get("raw_text") or "")
        comp, meta = compress_ijeoma_cjk_substitution(
            raw, lex_path, marker_strategy=args.marker_strategy
        )
        o2_r = len(enc.encode(raw))
        o2_c = len(enc.encode(comp))
        o2_rate = _o200k_saving_rate(o2_r, o2_c)
        sum_raw_o2 += o2_r
        sum_comp_o2 += o2_c
        per_case_rates.append(o2_rate)
        proxy_rates.append(float(meta.get("token_saving_rate_proxy") or 0.0))
        if o2_rate < 0:
            negative_o2_cases += 1
        rows.append(
            {
                "case_id": case.get("id"),
                "proxy_saving": meta.get("token_saving_rate_proxy"),
                "o200k_raw": o2_r,
                "o200k_compressed": o2_c,
                "o200k_saving_rate": round(o2_rate, 6),
                "replacements": meta.get("replacements"),
            }
        )

    corpus_o2 = _o200k_saving_rate(sum_raw_o2, sum_comp_o2)
    mean_per_case_o2 = sum(per_case_rates) / len(per_case_rates) if per_case_rates else 0.0
    mean_proxy = sum(proxy_rates) / len(proxy_rates) if proxy_rates else 0.0

    out = {
        "schema": "comp_ijeoma_cjk_o200k_diagnosis_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "case_count": len(rows),
        "lexicon_json": str(lex_path.relative_to(ROOT)).replace("\\", "/"),
        "marker_strategy": args.marker_strategy,
        "mean_token_saving_rate_proxy": round(mean_proxy, 6),
        "mean_o200k_saving_per_case": round(mean_per_case_o2, 6),
        "corpus_o200k_saving_rate": round(corpus_o2, 6),
        "negative_o200k_per_case_count": negative_o2_cases,
        "root_cause_hint": (
            "Proxy counts regex tokens (PUA marker often 1 token); o200k_base may assign "
            "multiple tokens to PUA/private-use chars or expand relative to multi-char Hanja. "
            "Report billing KPI should prefer corpus-level o200k (sum before/sum after), not "
            "mean of per-case globals when cases differ in length."
        ),
        "sample_worst_o200k": sorted(rows, key=lambda r: r["o200k_saving_rate"])[:5],
        "sample_best_o200k": sorted(rows, key=lambda r: r["o200k_saving_rate"], reverse=True)[:5],
        "rows": rows,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "wrote": out_path.name,
                "mean_proxy": mean_proxy,
                "corpus_o200k": corpus_o2,
                "mean_per_case_o2": mean_per_case_o2,
                "negative_cases": negative_o2_cases,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
