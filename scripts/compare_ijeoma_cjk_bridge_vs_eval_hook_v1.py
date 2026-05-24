#!/usr/bin/env python3
"""[HYPO] Parity: pre-bridge substitution vs evaluate_report CJK hook (B-track)."""

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
from scripts.ijeoma_cjk_compression_hypo_v1 import resolve_marker_strategy  # noqa: E402
from scripts.ijeoma_cjk_substitution_bench_bridge_v1 import apply_cjk_substitution_to_cases  # noqa: E402
from scripts.report_multilens_performance_eval import evaluate_report  # noqa: E402

DEFAULT_LANE = ROOT / "docs/final/artifacts/universal_compression_bench_lane_ijeoma_chunk_table_v1.json"
DEFAULT_LEX = ROOT / "reports/constitution/btrack_pilot/ijeoma_hanja_codebook_lexicon_v1_hypo_latest.json"
OUT = ROOT / "reports/constitution/btrack_pilot/comp_ijeoma_cjk_bridge_vs_eval_hook_v1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _case_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    cm = report.get("compression_metrics") or {}
    return list(cm.get("cases") or [])


def _metrics(report: dict[str, Any]) -> dict[str, float]:
    cm = report.get("compression_metrics") or {}
    rows = _case_rows(report)
    row0 = rows[0] if rows else {}
    return {
        "global_token_saving_rate": float(cm.get("global_token_saving_rate") or 0.0),
        "avg_reconstruction_fidelity_jaccard": float(
            cm.get("avg_reconstruction_fidelity_jaccard") or 0.0
        ),
        "compressed_tokens": float(row0.get("compressed_tokens") or 0.0),
        "raw_tokens": float(row0.get("raw_tokens") or 0.0),
    }


def _eval_one(
    case: dict[str, Any],
    *,
    use_hook: bool,
    lex: Path,
    marker_strategy: str,
) -> tuple[dict[str, float], str]:
    src = {"schema": "multilens_performance_eval_input_v1", "compression_cases": [case]}
    kw: dict[str, Any] = {
        "mode": "baseline",
        "use_master_codebook_lexicon_v1": False,
        "must_keep": set(BASE_MUST_KEEP),
        "graph_wire_selective_bridge": False,
    }
    if use_hook:
        kw["ijeoma_cjk_substitution_hypo_v1"] = True
        kw["ijeoma_cjk_substitution_lexicon_path"] = lex
        kw["ijeoma_cjk_marker_strategy"] = marker_strategy
    report = evaluate_report(src, source_input="btrack_pilot/ijeoma_cjk_parity", **kw)
    rows = _case_rows(report)
    comp_eff = str((rows[0] or {}).get("compressed_text_effective") or "")
    return _metrics(report), comp_eff


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lane-json", type=Path, default=DEFAULT_LANE)
    ap.add_argument("--lexicon-json", type=Path, default=DEFAULT_LEX)
    ap.add_argument("--out-json", type=Path, default=OUT)
    ap.add_argument("--max-cases", type=int, default=0)
    ap.add_argument(
        "--marker-strategy",
        choices=("pua", "ascii_compact", "atom_id", "o200k_tight"),
        default=None,
        help="Default: resolve_marker_strategy() (env MKM_IJEOMA_CJK_MARKER_STRATEGY).",
    )
    args = ap.parse_args()

    lane_path = (ROOT / args.lane_json).resolve() if not args.lane_json.is_absolute() else args.lane_json
    lex_path = (ROOT / args.lexicon_json).resolve() if not args.lexicon_json.is_absolute() else args.lexicon_json
    out_path = (ROOT / args.out_json).resolve() if not args.out_json.is_absolute() else args.out_json

    doc = json.loads(lane_path.read_text(encoding="utf-8"))
    cases = list(doc.get("compression_cases") or [])
    if args.max_cases > 0:
        cases = cases[: args.max_cases]

    marker_strategy = resolve_marker_strategy(args.marker_strategy)
    bridged, _ = apply_cjk_substitution_to_cases(
        cases, lex_path, marker_strategy=marker_strategy
    )

    rows: list[dict[str, Any]] = []
    saving_deltas: list[float] = []
    jaccard_deltas: list[float] = []
    comp_text_mismatch = 0

    for raw_case, br_case in zip(cases, bridged):
        hook_case = dict(raw_case)
        hook_case["lane_id"] = "ijeoma_chunk_table_v1"
        hook_case["domain"] = "ijeoma_sasang"
        hook_case["ijeoma_cjk_substitution_hypo_v1"] = True

        m_bridge, br_comp = _eval_one(
            br_case, use_hook=False, lex=lex_path, marker_strategy=marker_strategy
        )
        m_hook, hook_comp = _eval_one(
            hook_case, use_hook=True, lex=lex_path, marker_strategy=marker_strategy
        )

        ds = m_hook["global_token_saving_rate"] - m_bridge["global_token_saving_rate"]
        dj = m_hook["avg_reconstruction_fidelity_jaccard"] - m_bridge["avg_reconstruction_fidelity_jaccard"]
        saving_deltas.append(ds)
        jaccard_deltas.append(dj)

        if br_comp != hook_comp:
            comp_text_mismatch += 1

        rows.append(
            {
                "case_id": raw_case.get("id"),
                "bridge": m_bridge,
                "eval_hook": m_hook,
                "delta_saving": round(ds, 6),
                "delta_jaccard": round(dj, 6),
                "compressed_text_match": br_comp == hook_comp,
            }
        )

    max_abs_saving = max((abs(x) for x in saving_deltas), default=0.0)
    max_abs_jaccard = max((abs(x) for x in jaccard_deltas), default=0.0)
    parity_ok = max_abs_saving < 1e-9 and max_abs_jaccard < 1e-9 and comp_text_mismatch == 0

    out = {
        "schema": "comp_ijeoma_cjk_bridge_vs_eval_hook_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "lane_json": str(lane_path.relative_to(ROOT)).replace("\\", "/"),
        "case_count": len(rows),
        "marker_strategy": marker_strategy,
        "parity_ok": parity_ok,
        "max_abs_delta_saving": max_abs_saving,
        "max_abs_delta_jaccard": max_abs_jaccard,
        "compressed_text_mismatch_count": comp_text_mismatch,
        "mean_delta_saving": sum(saving_deltas) / len(saving_deltas) if saving_deltas else 0.0,
        "rows_sample": rows[:5],
        "rows_truncated": len(rows) > 5,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": out_path.name, "parity_ok": parity_ok, "case_count": len(rows)}, ensure_ascii=False))
    return 0 if parity_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
