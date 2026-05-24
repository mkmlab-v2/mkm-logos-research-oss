#!/usr/bin/env python3
"""[HYPO] Compare lexicon modes on IJEOMA chunk cases — never writes Track A active."""

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
)
from scripts.compression_profile_v1 import profile_evaluate_report_kwargs  # noqa: E402
from scripts.core.master_codebook_lexicon_v1_bridge import (  # noqa: E402
    lexicon_hits_for_text,
    resolve_latest_codebook_path,
)
from scripts.report_multilens_performance_eval import evaluate_report  # noqa: E402

CHUNK_LANE = ROOT / "docs/final/artifacts/universal_compression_bench_lane_ijeoma_chunk_table_v1.json"
HYPO_LEXICON = ROOT / "reports/constitution/btrack_pilot/ijeoma_hanja_codebook_lexicon_v1_hypo_latest.json"
OUT = ROOT / "reports/constitution/btrack_pilot/comp_hanja_chunk_compression_hypo_eval_v1.json"

MODES = (
    ("baseline_global_lexicon", {"min_token_len": 2, "include_cjk_bigrams": False, "lexicon": "global"}),
    ("ijeoma_hanja_lexicon", {"min_token_len": 2, "include_cjk_bigrams": True, "lexicon": "hypo"}),
    ("baseline_global_lexicon_min1", {"min_token_len": 1, "include_cjk_bigrams": False, "lexicon": "global"}),
    ("ijeoma_hanja_lexicon_min1", {"min_token_len": 1, "include_cjk_bigrams": True, "lexicon": "hypo"}),
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _case_metrics(report: dict[str, Any], case_id: str) -> dict[str, Any]:
    for row in (report.get("compression_metrics") or {}).get("cases") or []:
        if row.get("id") == case_id:
            return row
    return {}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lane-json", type=Path, default=CHUNK_LANE)
    ap.add_argument("--max-cases", type=int, default=10)
    ap.add_argument("--out-json", type=Path, default=OUT)
    ap.add_argument("--lexicon-json", type=Path, default=HYPO_LEXICON)
    args = ap.parse_args()

    lane_path = (ROOT / args.lane_json).resolve() if not args.lane_json.is_absolute() else args.lane_json
    out_path = (ROOT / args.out_json).resolve() if not args.out_json.is_absolute() else args.out_json
    doc = json.loads(lane_path.read_text(encoding="utf-8"))
    cases = (doc.get("compression_cases") or [])[: max(1, args.max_cases)]
    global_lex = resolve_latest_codebook_path()
    hypo_lex = (ROOT / args.lexicon_json).resolve() if not args.lexicon_json.is_absolute() else args.lexicon_json
    if not hypo_lex.is_file():
        print(json.dumps({"error": "hypo_lexicon_missing", "path": str(hypo_lex)}, ensure_ascii=False))
        return 2

    kw = _base_eval_kwargs()
    kw.update(profile_evaluate_report_kwargs("economy"))
    kw["use_master_codebook_lexicon_v1"] = True

    rows: list[dict[str, Any]] = []
    for case in cases:
        cid = str(case.get("id") or "")
        raw = str(case.get("raw_text") or "")
        src = {"schema": "multilens_performance_eval_input_v1", "compression_cases": [case]}
        mode_results: dict[str, Any] = {}
        for mode_name, opts_raw in MODES:
            opts = dict(opts_raw)
            lex_kind = opts.pop("lexicon", "global")
            lex_path = hypo_lex if lex_kind == "hypo" else global_lex
            if not lex_path or not lex_path.is_file():
                mode_results[mode_name] = {"error": "lexicon_missing"}
                continue
            hits, hit_meta = lexicon_hits_for_text(raw, lex_path, **opts)
            must_keep = set(BASE_MUST_KEEP) | hits
            eval_kw = dict(kw)
            eval_kw["master_codebook_lexicon_path"] = str(lex_path)
            report = evaluate_report(
                src,
                must_keep=must_keep,
                graph_wire_selective_bridge=False,
                **eval_kw,
            )
            cm = _case_metrics(report, cid)
            mode_results[mode_name] = {
                "lexicon_hit_count": hit_meta.get("hit_count"),
                "token_saving_rate": cm.get("token_saving_rate"),
                "reconstruction_fidelity_jaccard": cm.get("reconstruction_fidelity_jaccard"),
            }
        rows.append({"case_id": cid, "modes": mode_results})

    best_mode = None
    best_mean = -1.0
    for mode_name, _ in MODES:
        vals = [
            float(r["modes"][mode_name]["token_saving_rate"] or 0)
            for r in rows
            if r["modes"].get(mode_name)
        ]
        if vals:
            m = sum(vals) / len(vals)
            if m > best_mean:
                best_mean, best_mode = m, mode_name

    out = {
        "schema": "comp_hanja_chunk_compression_hypo_eval_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "cases_evaluated": len(rows),
        "best_mode_by_mean_saving": best_mode,
        "best_mean_token_saving_rate": round(best_mean, 4),
        "rows": rows,
        "recommendation": (
            "Promote cjk_bigram lexicon path to B-track lane hook if mean saving > 0; "
            "else build 수세보원 phrase slice — not Track A."
        ),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "wrote": out_path.name,
                "best_mode": best_mode,
                "best_mean_saving": best_mean,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
