#!/usr/bin/env python3
"""Sweep Universal Matrix bench with B-track profiles — never writes Track A active."""

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
from scripts.report_multilens_performance_eval import evaluate_report  # noqa: E402

MATRIX_INPUT = ROOT / "docs/final/artifacts/UNIVERSAL_COMPRESSION_BENCH_MATRIX_INPUT_V1.json"
OUT = ROOT / "reports/constitution/btrack_pilot/comp_universal_bench_matrix_sweep_v1.json"
FORBIDDEN = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _eval_profile(
    src: dict[str, Any],
    *,
    wire: bool,
    eval_mode: str = "experimental",
    cjk_eval_hook: bool = False,
    cjk_lexicon_path: Path | None = None,
) -> dict[str, Any]:
    kw = _base_eval_kwargs()
    if eval_mode == "baseline":
        kw["mode"] = "baseline"
        kw["use_master_codebook_lexicon_v1"] = False
    else:
        prof = profile_evaluate_report_kwargs("economy")
        kw.update(prof)
    if wire:
        kw["apply_gematria_4d_bridge_policy"] = False
    if cjk_eval_hook:
        from scripts.ijeoma_cjk_compression_hypo_v1 import (  # noqa: WPS433
            resolve_marker_strategy,
            resolve_shorter_by,
        )

        kw["ijeoma_cjk_substitution_hypo_v1"] = True
        if cjk_lexicon_path is not None:
            kw["ijeoma_cjk_substitution_lexicon_path"] = cjk_lexicon_path
        kw["ijeoma_cjk_marker_strategy"] = resolve_marker_strategy()
        kw["ijeoma_cjk_shorter_by"] = resolve_shorter_by()
    report = evaluate_report(
        src,
        must_keep=set(BASE_MUST_KEEP),
        graph_wire_selective_bridge=wire,
        emit_semantic_pointer=True,
        **kw,
    )
    return _metrics(report)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=MATRIX_INPUT)
    parser.add_argument("--out-json", type=Path, default=OUT)
    parser.add_argument("--max-cases", type=int, default=0, help="0 = all cases")
    parser.add_argument(
        "--exclude-lane-id",
        action="append",
        default=[],
        help="Repeatable; e.g. ijeoma_chunk_table_v1 for operational KPI sweep.",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--eval-mode",
        choices=("experimental", "baseline"),
        default="experimental",
        help="baseline honors case compressed_text (CJK substitution lane).",
    )
    parser.add_argument(
        "--apply-cjk-substitution",
        action="store_true",
        help="PUA substitution on cases before eval; uses --cjk-lexicon-json.",
    )
    parser.add_argument(
        "--cjk-lexicon-json",
        type=Path,
        default=ROOT / "reports/constitution/btrack_pilot/ijeoma_hanja_codebook_lexicon_v1_hypo_latest.json",
    )
    parser.add_argument(
        "--eval-report-cjk-hook",
        action="store_true",
        help="Opt-in evaluate_report ijeoma_cjk_substitution_hypo_v1 (per-case, no pre-bridge).",
    )
    args = parser.parse_args()

    in_path = (ROOT / args.input).resolve() if not args.input.is_absolute() else args.input.resolve()
    if not in_path.is_file():
        print(json.dumps({"error": "matrix_input_missing", "path": str(in_path)}))
        return 2

    doc = json.loads(in_path.read_text(encoding="utf-8"))
    cases = list(doc.get("compression_cases") or [])
    eval_mode = args.eval_mode
    lex_path = (
        (ROOT / args.cjk_lexicon_json).resolve()
        if not args.cjk_lexicon_json.is_absolute()
        else args.cjk_lexicon_json.resolve()
    )
    if args.apply_cjk_substitution:
        from scripts.ijeoma_cjk_substitution_bench_bridge_v1 import (  # noqa: WPS433
            apply_cjk_substitution_to_cases,
        )

        cases, _ = apply_cjk_substitution_to_cases(cases, lex_path)
        if eval_mode == "experimental":
            eval_mode = "baseline"
    exclude = set(args.exclude_lane_id or [])
    if exclude:
        cases = [c for c in cases if str(c.get("lane_id") or "") not in exclude]
    if args.max_cases > 0:
        cases = cases[: args.max_cases]

    out_path = (ROOT / args.out_json).resolve() if not args.out_json.is_absolute() else args.out_json
    cjk_hook = bool(args.eval_report_cjk_hook) or bool(args.apply_cjk_substitution)

    if args.dry_run:
        print(
            json.dumps(
                {
                    "dry_run": True,
                    "case_count": len(cases),
                    "excluded_lane_ids": sorted(exclude),
                    "out_json": str(out_path.relative_to(ROOT)).replace("\\", "/"),
                    "forbidden_write": str(FORBIDDEN.name),
                },
                ensure_ascii=False,
            )
        )
        return 0

    rows: list[dict[str, Any]] = []
    for case in cases:
        src = {
            "schema": "multilens_performance_eval_input_v1",
            "compression_cases": [case],
        }
        economy = _eval_profile(
            src,
            wire=False,
            eval_mode=eval_mode,
            cjk_eval_hook=cjk_hook,
            cjk_lexicon_path=lex_path if cjk_hook else None,
        )
        wire = _eval_profile(
            src,
            wire=True,
            eval_mode=eval_mode,
            cjk_eval_hook=cjk_hook,
            cjk_lexicon_path=lex_path if cjk_hook else None,
        )
        rows.append(
            {
                "case_id": case.get("id"),
                "domain_tag": case.get("domain_tag"),
                "lane_id": case.get("lane_id"),
                "economy": economy,
                "economy_plus_wire": wire,
            }
        )

    def _agg(key: str) -> dict[str, float]:
        vals = [float(r["economy_plus_wire"][key]) for r in rows if r["economy_plus_wire"].get(key) is not None]
        if not vals:
            return {}
        return {"mean": sum(vals) / len(vals), "min": min(vals), "max": max(vals)}

    out_doc = {
        "schema": "comp_universal_bench_matrix_sweep_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "bench_label": "universal_matrix_v1",
        "input": str(in_path.relative_to(ROOT)).replace("\\", "/"),
        "excluded_lane_ids": sorted(exclude) if exclude else [],
        "eval_mode": eval_mode,
        "cjk_substitution_applied": bool(args.apply_cjk_substitution),
        "eval_report_cjk_hook": bool(args.eval_report_cjk_hook),
        "case_count": len(rows),
        "profiles": {
            "economy": _agg("global_token_saving_rate") if rows else {},
            "economy_plus_wire": _agg("global_token_saving_rate"),
        },
        "jaccard_aggregate": {
            "economy": _agg("avg_reconstruction_fidelity_jaccard"),
            "economy_plus_wire": _agg("avg_reconstruction_fidelity_jaccard"),
        },
        "track_a_active_written": False,
        "forbidden_write_path": str(FORBIDDEN.relative_to(ROOT)).replace("\\", "/"),
        "rows": rows,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "wrote": str(out_path.relative_to(ROOT)).replace("\\", "/"),
                "case_count": len(rows),
                "excluded_lane_ids": sorted(exclude),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
