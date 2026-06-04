#!/usr/bin/env python3
"""[HYPO] Golden-40: NG-40 eval lane + salience PoC + per-case oracle Jaccard upper bound.

Oracle hybrid is research-only (picks best recon per case); not a deployable codec.
"""
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

from scripts.nextgen_latent_codec_v1 import jaccard_text, latent_salience_reconstruct
from scripts.run_nextgen_latent_indexer_eval_ng40_v1 import (  # noqa: E402
    ACTIVE,
    INPUT_V2,
    _beat,
    _frozen_active,
    _metrics,
    evaluate_ng40_lane,
)

DEFAULT_BEST_CAPS = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_latent_eval_best_v1_latest.json"
)
DEFAULT_OUT = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_latent_poc_eval_hybrid_v1_latest.json"
)
POC_KEEP_GRID = (0.80, 0.82, 0.84, 0.86, 0.88, 0.90, 0.92)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _case_map(doc_in: dict[str, Any]) -> dict[str, str]:
    return {
        str(c.get("id")): str(c.get("raw_text") or "")
        for c in (doc_in.get("compression_cases") or [])
        if c.get("id")
    }


def _aggregate_from_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total_raw = sum(r["raw_chars"] for r in rows)
    total_comp = sum(r["compressed_chars"] for r in rows)
    jacc_sum = sum(r["reconstruction_fidelity_jaccard"] for r in rows)
    n = len(rows)
    return {
        "case_count": n,
        "global_token_saving_rate": round(1.0 - (total_comp / max(1, total_raw)), 6),
        "avg_reconstruction_fidelity_jaccard": round(jacc_sum / max(1, n), 6),
        "min_reconstruction_fidelity_jaccard": round(
            min((r["reconstruction_fidelity_jaccard"] for r in rows), default=0.0), 6
        ),
    }


def _poc_rows(raw_by_id: dict[str, str], keep_ratio: float) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for cid, raw in raw_by_id.items():
        comp, recon = latent_salience_reconstruct(raw, keep_ratio)
        raw_len = max(1, len(raw))
        rows.append(
            {
                "id": cid,
                "raw_chars": len(raw),
                "compressed_chars": len(comp),
                "keep_ratio": keep_ratio,
                "token_saving_rate": round(1.0 - len(comp) / raw_len, 6),
                "reconstruction_fidelity_jaccard": round(jaccard_text(raw, recon), 6),
            }
        )
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bench-input", type=Path, default=INPUT_V2)
    ap.add_argument(
        "--caps-json",
        type=Path,
        default=DEFAULT_BEST_CAPS,
        help="Read general/sensitive/hangul caps from ng40 eval JSON run_config_summary",
    )
    ap.add_argument("--general-cap", type=float, default=None)
    ap.add_argument("--sensitive-cap", type=float, default=None)
    ap.add_argument("--hangul-cap", type=float, default=None)
    ap.add_argument(
        "--poc-keep-grid",
        nargs="*",
        type=float,
        default=None,
        help="Salience keep_ratio grid (default 0.80–0.92)",
    )
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.bench_input.is_file():
        print(f"error: missing {args.bench_input}", file=sys.stderr)
        return 1

    g = args.general_cap
    s = args.sensitive_cap
    h = args.hangul_cap
    if args.caps_json.is_file():
        caps_doc = json.loads(args.caps_json.read_text(encoding="utf-8"))
        rc = caps_doc.get("run_config_summary") or {}
        g = g if g is not None else float(rc.get("general_max_saving_rate") or 0.31)
        s = s if s is not None else float(rc.get("sensitive_max_saving_rate") or 0.27)
        h = h if h is not None else float(rc.get("hangul_max_saving_rate") or 0.54)
    else:
        g, s, h = g or 0.31, s or 0.27, h or 0.54

    doc_in = json.loads(args.bench_input.read_text(encoding="utf-8"))
    raw_by_id = _case_map(doc_in)
    baseline_j = 0.0
    baseline_path = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_REPORT_V2.json"
    if baseline_path.is_file():
        bdoc = json.loads(baseline_path.read_text(encoding="utf-8"))
        baseline_j = float(
            bdoc.get("compression_metrics", {}).get(
                "avg_reconstruction_fidelity_jaccard", 0.0
            )
        )

    eval_agg, eval_report = evaluate_ng40_lane(
        doc_in,
        bench_input=args.bench_input,
        general_cap=float(g),
        sensitive_cap=float(s),
        hangul_cap=float(h),
        baseline_j=baseline_j,
        use_domain_relaxed=False,
        use_master_codebook_lexicon_v1=False,
        active_track_parity=False,
    )
    frozen = _frozen_active()

    eval_rows: list[dict[str, Any]] = []
    for c in (eval_report.get("compression_metrics") or {}).get("cases") or []:
        cid = str(c.get("id"))
        raw = raw_by_id.get(cid, "")
        recon = str(c.get("reconstructed_text_effective") or "")
        raw_len = max(1, len(raw))
        comp_len = len(str(c.get("compressed_text_effective") or ""))
        eval_rows.append(
            {
                "id": cid,
                "raw_chars": len(raw),
                "compressed_chars": comp_len,
                "token_saving_rate": round(1.0 - comp_len / raw_len, 6),
                "reconstruction_fidelity_jaccard": float(
                    c.get("reconstruction_fidelity_jaccard") or 0
                ),
            }
        )

    grid = list(args.poc_keep_grid or POC_KEEP_GRID)
    poc_sweep: list[dict[str, Any]] = []
    best_poc_kr = grid[0]
    best_poc_agg: dict[str, Any] = {}
    for kr in grid:
        rows = _poc_rows(raw_by_id, kr)
        agg = _aggregate_from_rows(rows)
        poc_sweep.append(
            {
                "keep_ratio": kr,
                "aggregate": agg,
                "beat_check": _beat(agg, frozen),
            }
        )
        if not best_poc_agg or float(agg.get("avg_reconstruction_fidelity_jaccard") or 0) >= float(
            best_poc_agg.get("avg_reconstruction_fidelity_jaccard") or 0
        ):
            best_poc_agg = agg
            best_poc_kr = kr

    poc_rows = _poc_rows(raw_by_id, best_poc_kr)
    poc_by_id = {r["id"]: r for r in poc_rows}

    oracle_rows: list[dict[str, Any]] = []
    for er in eval_rows:
        cid = er["id"]
        pr = poc_by_id.get(cid, {})
        j_eval = float(er["reconstruction_fidelity_jaccard"])
        j_poc = float(pr.get("reconstruction_fidelity_jaccard") or 0)
        pick = "eval" if j_eval >= j_poc else "poc"
        j_best = max(j_eval, j_poc)
        oracle_rows.append(
            {
                "id": cid,
                "oracle_pick": pick,
                "eval_jaccard": j_eval,
                "poc_jaccard": j_poc,
                "oracle_jaccard": round(j_best, 6),
                "eval_saving": er.get("token_saving_rate"),
                "poc_saving": pr.get("token_saving_rate"),
            }
        )

    oracle_jaccard_only = {
        "case_count": len(oracle_rows),
        "avg_reconstruction_fidelity_jaccard": round(
            sum(r["oracle_jaccard"] for r in oracle_rows) / max(1, len(oracle_rows)), 6
        ),
        "min_reconstruction_fidelity_jaccard": round(
            min((r["oracle_jaccard"] for r in oracle_rows), default=0.0), 6
        ),
        "note": "Per-case max(eval_jaccard, poc_jaccard); no single codec saving rate",
    }

    out = {
        "schema": "nextgen_latent_poc_eval_hybrid_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "track_a_active_write": False,
        "golden40_compatible": True,
        "eval_caps": {
            "general_max_saving_rate": g,
            "sensitive_max_saving_rate": s,
            "hangul_max_saving_rate": h,
            "caps_source": str(args.caps_json.relative_to(ROOT)).replace("\\", "/")
            if args.caps_json.is_file()
            else "cli",
        },
        "eval_lane": {
            "aggregate": eval_agg,
            "beat_check": _beat(eval_agg, frozen),
            "per_case_count": len(eval_rows),
        },
        "poc_lane": {
            "selected_keep_ratio": best_poc_kr,
            "aggregate": best_poc_agg,
            "beat_check": _beat(best_poc_agg, frozen),
            "sweep": poc_sweep,
        },
        "oracle_jaccard_upper_bound": {
            "aggregate": oracle_jaccard_only,
            "beat_check_jaccard_only": {
                "beats_frozen_jaccard": float(
                    oracle_jaccard_only["avg_reconstruction_fidelity_jaccard"]
                )
                >= float(frozen.get("avg_reconstruction_fidelity_jaccard") or 0)
                if frozen.get("present")
                else False,
                "delta_jaccard_pp": round(
                    (
                        float(oracle_jaccard_only["avg_reconstruction_fidelity_jaccard"])
                        - float(frozen.get("avg_reconstruction_fidelity_jaccard") or 0)
                    )
                    * 100,
                    2,
                )
                if frozen.get("present")
                else None,
            },
            "per_case": oracle_rows,
        },
        "frozen_baseline_parallel": frozen,
        "guardrails": [
            "Oracle hybrid is not an implementation; eval remains production-shaped path",
            "PoC does not beat frozen on saving; do not merge into Track A",
            "41k lexicon OFF on eval lane",
        ],
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "wrote": str(args.out_json),
                "eval_beat": out["eval_lane"]["beat_check"]["beat_frozen"],
                "eval_saving": eval_agg.get("global_token_saving_rate"),
                "eval_jaccard": eval_agg.get("avg_reconstruction_fidelity_jaccard"),
                "poc_kr": best_poc_kr,
                "poc_jaccard": best_poc_agg.get("avg_reconstruction_fidelity_jaccard"),
                "oracle_jaccard": oracle_jaccard_only["avg_reconstruction_fidelity_jaccard"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
