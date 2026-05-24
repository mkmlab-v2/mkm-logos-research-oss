#!/usr/bin/env python3
"""[HYPO] o200k token saving for CJK substitution lane vs token-proxy (B-track)."""

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
from scripts.ijeoma_cjk_compression_hypo_v1 import default_hypo_lexicon_path  # noqa: E402
from scripts.report_multilens_performance_eval import _o200k_saving_rate, evaluate_report  # noqa: E402

LANE = ROOT / "docs/final/artifacts/universal_compression_bench_lane_ijeoma_chunk_table_v1.json"
OUT = ROOT / "reports/constitution/btrack_pilot/comp_ijeoma_cjk_o200k_bench_v1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _mean_o200k(report: dict[str, Any]) -> float | None:
    cm = report.get("compression_metrics") or {}
    tt = cm.get("tiktoken_o200k") or {}
    return tt.get("global_token_saving_rate")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lane-json", type=Path, default=LANE)
    ap.add_argument("--lexicon-json", type=Path, default=None)
    ap.add_argument("--max-cases", type=int, default=0)
    ap.add_argument("--out-json", type=Path, default=OUT)
    args = ap.parse_args()

    lane_path = (ROOT / args.lane_json).resolve() if not args.lane_json.is_absolute() else args.lane_json
    lex_path = (
        Path(args.lexicon_json).resolve()
        if args.lexicon_json
        else default_hypo_lexicon_path()
    )
    out_path = (ROOT / args.out_json).resolve() if not args.out_json.is_absolute() else args.out_json

    cases = json.loads(lane_path.read_text(encoding="utf-8")).get("compression_cases") or []
    if args.max_cases > 0:
        cases = cases[: args.max_cases]

    proxy_rates: list[float] = []
    o200k_rates: list[float] = []
    total_o200k_raw = total_o200k_comp = 0
    tiktoken_ok = True
    err: str | None = None

    for case in cases:
        hc = dict(case)
        hc["lane_id"] = "ijeoma_chunk_table_v1"
        hc["domain"] = "ijeoma_sasang"
        src = {"compression_cases": [hc]}
        try:
            rep = evaluate_report(
                src,
                source_input="btrack_pilot/ijeoma_cjk_o200k",
                mode="baseline",
                use_master_codebook_lexicon_v1=False,
                must_keep=set(BASE_MUST_KEEP),
                ijeoma_cjk_substitution_hypo_v1=True,
                ijeoma_cjk_substitution_lexicon_path=lex_path,
                ijeoma_cjk_marker_strategy="ascii_compact",
                require_tiktoken_o200k=True,
            )
        except RuntimeError as e:
            tiktoken_ok = False
            err = str(e)
            break
        rows = (rep.get("compression_metrics") or {}).get("cases") or []
        if rows:
            proxy_rates.append(float(rows[0].get("token_saving_rate") or 0.0))
            r0 = rows[0]
            o2_r = int(r0.get("o200k_raw_tokens") or r0.get("o200k_tokens_before") or 0)
            o2_c = int(r0.get("o200k_compressed_tokens") or r0.get("o200k_tokens_after") or 0)
            total_o200k_raw += o2_r
            total_o200k_comp += o2_c
        o2 = _mean_o200k(rep)
        if o2 is not None:
            o200k_rates.append(float(o2))

    out = {
        "schema": "comp_ijeoma_cjk_o200k_bench_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "case_count": len(cases),
        "tiktoken_o200k_available": tiktoken_ok,
        "tiktoken_error": err,
        "mean_token_saving_rate_proxy": sum(proxy_rates) / len(proxy_rates) if proxy_rates else None,
        "mean_o200k_token_saving_rate": sum(o200k_rates) / len(o200k_rates) if o200k_rates else None,
        "corpus_o200k_token_saving_rate": _o200k_saving_rate(total_o200k_raw, total_o200k_comp)
        if total_o200k_raw
        else None,
        "o200k_tokens_raw_total": total_o200k_raw or None,
        "o200k_tokens_compressed_total": total_o200k_comp or None,
        "diagnosis_artifact": "reports/constitution/btrack_pilot/comp_ijeoma_cjk_o200k_diagnosis_v1.json",
        "note": "Separate KPI bucket; not Golden 40 / 290 MD mean. Prefer corpus_o200k over mean per-case when PUA markers skew o200k.",
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": out_path.name, "headline": out}, ensure_ascii=False))
    return 0 if tiktoken_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
