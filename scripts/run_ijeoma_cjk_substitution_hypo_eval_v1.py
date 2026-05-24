#!/usr/bin/env python3
"""[HYPO] Chunk lane eval: baseline fixture vs CJK atom substitution (B-track)."""

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

from scripts.comp_graphrag_philosophy_compression_sweep_v1 import BASE_MUST_KEEP, _metrics  # noqa: E402
from scripts.ijeoma_cjk_compression_hypo_v1 import (  # noqa: E402
    compress_ijeoma_cjk_substitution,
    expand_ijeoma_cjk_substitution,
    resolve_marker_strategy,
)
from scripts.report_multilens_performance_eval import evaluate_report  # noqa: E402

CHUNK_LANE = ROOT / "docs/final/artifacts/universal_compression_bench_lane_ijeoma_chunk_table_v1.json"
HYPO_LEX = ROOT / "reports/constitution/btrack_pilot/ijeoma_hanja_codebook_lexicon_v1_hypo_latest.json"
OUT = ROOT / "reports/constitution/btrack_pilot/comp_ijeoma_cjk_substitution_hypo_eval_v1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _jaccard(a: str, b: str) -> float:
    sa = set(a.split())
    sb = set(b.split())
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lane-json", type=Path, default=CHUNK_LANE)
    ap.add_argument("--lexicon-json", type=Path, default=HYPO_LEX)
    ap.add_argument("--max-cases", type=int, default=10)
    ap.add_argument("--out-json", type=Path, default=OUT)
    ap.add_argument(
        "--marker-strategy",
        choices=("pua", "ascii_compact", "atom_id", "o200k_tight"),
        default=None,
        help="Default ascii_compact via resolve_marker_strategy when omitted.",
    )
    args = ap.parse_args()

    lane_path = (ROOT / args.lane_json).resolve() if not args.lane_json.is_absolute() else args.lane_json
    lex_path = (ROOT / args.lexicon_json).resolve() if not args.lexicon_json.is_absolute() else args.lexicon_json
    out_path = (ROOT / args.out_json).resolve() if not args.out_json.is_absolute() else args.out_json
    if not lex_path.is_file():
        print(json.dumps({"error": "lexicon_missing"}, ensure_ascii=False))
        return 2

    marker_strategy = resolve_marker_strategy(args.marker_strategy)
    doc = json.loads(lane_path.read_text(encoding="utf-8"))
    cases = list(doc.get("compression_cases") or [])
    if args.max_cases > 0:
        cases = cases[: args.max_cases]
    rows: list[dict[str, Any]] = []

    for case in cases:
        cid = str(case.get("id") or "")
        raw = str(case.get("raw_text") or "")
        fixture_comp = str(case.get("compressed_text") or "")
        cjk_comp, sub_meta = compress_ijeoma_cjk_substitution(
            raw, lex_path, marker_strategy=marker_strategy
        )
        cjk_rec = expand_ijeoma_cjk_substitution(
            cjk_comp, lex_path, marker_strategy=marker_strategy
        )

        def _eval_fixture(comp: str, rec: str) -> dict[str, Any]:
            src = {
                "schema": "multilens_performance_eval_input_v1",
                "compression_cases": [
                    {**case, "compressed_text": comp, "reconstructed_text": rec}
                ],
            }
            report = evaluate_report(
                src,
                source_input="docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json",
                must_keep=set(BASE_MUST_KEEP),
                mode="baseline",
                use_master_codebook_lexicon_v1=False,
                graph_wire_selective_bridge=False,
            )
            cm = (report.get("compression_metrics") or {}).get("cases") or []
            row = cm[0] if cm else {}
            return {
                "token_saving_rate": row.get("token_saving_rate"),
                "reconstruction_fidelity_jaccard": row.get("reconstruction_fidelity_jaccard"),
            }

        rows.append(
            {
                "case_id": cid,
                "substitution_meta": sub_meta,
                "fixture_baseline": _eval_fixture(fixture_comp, fixture_comp),
                "cjk_atom_substitution": _eval_fixture(cjk_comp, cjk_rec),
                "local_jaccard_substitution": round(_jaccard(raw, cjk_rec), 4),
            }
        )

    subst_savings = [
        float(r["cjk_atom_substitution"]["token_saving_rate"] or 0) for r in rows
    ]
    mean_saving = sum(subst_savings) / len(subst_savings) if subst_savings else 0.0

    out = {
        "schema": "comp_ijeoma_cjk_substitution_hypo_eval_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "cases_evaluated": len(rows),
        "marker_strategy": marker_strategy,
        "mean_token_saving_rate_cjk_substitution": round(mean_saving, 4),
        "root_cause_note": "evaluate_report WORD_RE excludes hanja; substitution bypasses _compress_experimental",
        "rows": rows,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": out_path.name, "mean_saving": mean_saving}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
