#!/usr/bin/env python3
"""Wire AB on one Universal Matrix lane — B-track; Golden 40 / active report untouched."""

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

from scripts.comp_graphrag_philosophy_compression_sweep_v1 import (  # noqa: E402
    BASE_MUST_KEEP,
    _base_eval_kwargs,
    _metrics,
)
from scripts.compression_profile_v1 import profile_evaluate_report_kwargs  # noqa: E402
from scripts.mkm_graph_wire_bridge_influence_v1 import (  # noqa: E402
    build_influence_map_from_compression_cases,
    wire_atom_ids_default,
)
from scripts.report_multilens_performance_eval import evaluate_report  # noqa: E402

LANE_INPUTS: dict[str, Path] = {
    "finance": ROOT / "docs/final/artifacts/finance_macro_b2b_compression_eval_input_v1.json",
    "enterprise": ROOT
    / "docs/final/artifacts/universal_compression_bench_lane_enterprise_general_v1.json",
    "ijeoma": ROOT / "docs/final/artifacts/universal_compression_bench_lane_ijeoma_sasang_v1.json",
    "ijeoma_chunk": ROOT
    / "docs/final/artifacts/universal_compression_bench_lane_ijeoma_chunk_table_v1.json",
}
GOLDEN_INPUT = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
FORBIDDEN_ACTIVE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
PILOT = ROOT / "reports/constitution/btrack_pilot"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _eval_economy_batch(
    src: dict[str, Any],
    *,
    wire: bool,
    influence: dict[str, dict[str, Any]],
    master_codebook_lexicon_path: Path | None = None,
    eval_mode: str = "experimental",
) -> dict[str, Any]:
    kw = _base_eval_kwargs()
    if eval_mode == "baseline":
        kw["mode"] = "baseline"
        kw["use_master_codebook_lexicon_v1"] = False
    elif wire:
        kw["apply_gematria_4d_bridge_policy"] = False
    else:
        kw.update(profile_evaluate_report_kwargs("economy"))
    if eval_mode != "baseline" and master_codebook_lexicon_path is not None and master_codebook_lexicon_path.is_file():
        kw["use_master_codebook_lexicon_v1"] = True
        kw["master_codebook_lexicon_path"] = str(master_codebook_lexicon_path.resolve())
    report = evaluate_report(
        src,
        must_keep=set(BASE_MUST_KEEP),
        graph_wire_selective_bridge=wire,
        case_graph_wire_influence=influence if wire else None,
        emit_semantic_pointer=True,
        **kw,
    )
    return _metrics(report)


def _delta_pp(a: float | None, b: float | None) -> float | None:
    if a is None or b is None:
        return None
    return round((b - a) * 100.0, 4)


def run_lane(
    *,
    lane_key: str,
    input_path: Path,
    out_path: Path,
    master_codebook_lexicon_path: Path | None = None,
    eval_mode: str = "experimental",
    apply_cjk_substitution: bool = False,
    cjk_lexicon_path: Path | None = None,
) -> dict[str, Any]:
    src = json.loads(input_path.read_text(encoding="utf-8"))
    cases = list(src.get("compression_cases") or [])
    if apply_cjk_substitution:
        from scripts.ijeoma_cjk_substitution_bench_bridge_v1 import (  # noqa: WPS433
            apply_cjk_substitution_to_cases,
        )

        lex = cjk_lexicon_path or (
            ROOT / "reports/constitution/btrack_pilot/ijeoma_hanja_codebook_lexicon_v1_hypo_latest.json"
        )
        cases, sub_summary = apply_cjk_substitution_to_cases(cases, lex)
        src = dict(src)
        src["compression_cases"] = cases
        src["cjk_substitution_summary"] = sub_summary
        if eval_mode == "experimental":
            eval_mode = "baseline"
    influence = build_influence_map_from_compression_cases(
        cases, wire_atom_ids=wire_atom_ids_default()
    )
    boost_cases = sum(1 for v in influence.values() if v.get("bridge_boost"))
    routes_with_graph = sum(1 for v in influence.values() if int(v.get("expanded_node_count") or 0) > 0)

    economy = _eval_economy_batch(
        src,
        wire=False,
        influence=influence,
        master_codebook_lexicon_path=master_codebook_lexicon_path,
        eval_mode=eval_mode,
    )
    economy_wire = _eval_economy_batch(
        src,
        wire=True,
        influence=influence,
        master_codebook_lexicon_path=master_codebook_lexicon_path,
        eval_mode=eval_mode,
    )

    saving0 = economy.get("global_token_saving_rate")
    saving1 = economy_wire.get("global_token_saving_rate")
    j0 = economy.get("avg_reconstruction_fidelity_jaccard")
    j1 = economy_wire.get("avg_reconstruction_fidelity_jaccard")

    lane_id = str(src.get("lane_id") or lane_key)
    domain_tag = str(src.get("domain_tag") or lane_key)

    return {
        "schema": "comp_universal_bench_matrix_wire_ab_lane_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "lane_key": lane_key,
        "lane_id": lane_id,
        "domain_tag": domain_tag,
        "case_count": len(cases),
        "input_path": str(input_path.relative_to(ROOT)).replace("\\", "/"),
        "output_path": str(out_path.relative_to(ROOT)).replace("\\", "/"),
        "golden_frozen_pointer": str(GOLDEN_INPUT.relative_to(ROOT)).replace("\\", "/"),
        "active_report_untouched": True,
        "eval_mode": eval_mode,
        "cjk_substitution_applied": apply_cjk_substitution,
        "forbidden_write_path": str(FORBIDDEN_ACTIVE.relative_to(ROOT)).replace("\\", "/"),
        "graph_wire": {
            "wire_atom_ids_source": "wire_atom_ids_default()",
            "bridge_boost_cases": boost_cases,
            "cases_with_graph_expansion": routes_with_graph,
            "bridge_boost_min_score": 0.35,
        },
        "economy_baseline": economy,
        "economy_plus_wire_selective": economy_wire,
        "deltas_wire_vs_baseline": {
            "global_token_saving_rate_pp": _delta_pp(saving0, saving1),
            "avg_reconstruction_fidelity_jaccard_pp": _delta_pp(j0, j1),
        },
        "headline": {
            "economy_saving_pct": round(float(saving0 or 0) * 100, 2) if saving0 is not None else None,
            "wire_saving_pct": round(float(saving1 or 0) * 100, 2) if saving1 is not None else None,
            "economy_jaccard": j0,
            "wire_jaccard": j1,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--lane",
        choices=sorted(LANE_INPUTS),
        help="finance | enterprise | ijeoma | ijeoma_chunk",
    )
    parser.add_argument("--input", type=Path, default=None)
    parser.add_argument("--lane-json", type=Path, default=None, help="Alias for --input.")
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--out-json", type=Path, default=None, help="Alias for --out.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--lexicon-json",
        type=Path,
        default=None,
        help="Optional master_codebook_lexicon_v1 path (e.g. ijeoma_hanja hypo slice).",
    )
    parser.add_argument(
        "--eval-mode",
        choices=("experimental", "baseline"),
        default="experimental",
    )
    parser.add_argument(
        "--apply-cjk-substitution",
        action="store_true",
        help="PUA substitution pre-pass; forces baseline eval on fixtures.",
    )
    parser.add_argument("--cjk-lexicon-json", type=Path, default=None)
    args = parser.parse_args()

    if args.lane_json and not args.input:
        args.input = args.lane_json
    if args.out_json and not args.out:
        args.out = args.out_json

    if not args.lane and not args.input:
        parser.error("provide --lane or --input")

    lane_key = args.lane or "custom"
    in_path = args.input
    if in_path is None:
        in_path = LANE_INPUTS[args.lane]
    in_path = (ROOT / in_path).resolve() if not in_path.is_absolute() else in_path.resolve()

    if args.out:
        out_path = (ROOT / args.out).resolve() if not args.out.is_absolute() else args.out.resolve()
    else:
        suffix = lane_key if args.lane else "custom"
        out_path = PILOT / f"comp_universal_bench_matrix_wire_ab_{suffix}_v1.json"
        if suffix == "ijeoma_chunk":
            out_path = PILOT / "comp_universal_bench_matrix_wire_ab_ijeoma_chunk_v1.json"

    if not in_path.is_file():
        print(json.dumps({"error": "input_missing", "path": str(in_path)}, ensure_ascii=False))
        return 2

    if args.dry_run:
        doc = json.loads(in_path.read_text(encoding="utf-8"))
        print(
            json.dumps(
                {
                    "dry_run": True,
                    "lane_key": lane_key,
                    "case_count": len(doc.get("compression_cases") or []),
                    "out": str(out_path.relative_to(ROOT)).replace("\\", "/"),
                },
                ensure_ascii=False,
            )
        )
        return 0

    lex_path = None
    if args.lexicon_json:
        lex_path = (ROOT / args.lexicon_json).resolve() if not args.lexicon_json.is_absolute() else args.lexicon_json
    cjk_lex = None
    if args.cjk_lexicon_json:
        cjk_lex = (ROOT / args.cjk_lexicon_json).resolve() if not args.cjk_lexicon_json.is_absolute() else args.cjk_lexicon_json
    doc = run_lane(
        lane_key=lane_key,
        input_path=in_path,
        out_path=out_path,
        master_codebook_lexicon_path=lex_path,
        eval_mode=args.eval_mode,
        apply_cjk_substitution=bool(args.apply_cjk_substitution),
        cjk_lexicon_path=cjk_lex,
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "wrote": out_path.name,
                "lane_key": lane_key,
                "case_count": doc["case_count"],
                "bridge_boost_cases": doc["graph_wire"]["bridge_boost_cases"],
                "deltas": doc["deltas_wire_vs_baseline"],
                "headline": doc["headline"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
