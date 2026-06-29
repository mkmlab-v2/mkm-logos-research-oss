#!/usr/bin/env python3
"""[HYPO] Path A keep_ratio microgrid — byte_exact spine + Logos sidecar billable sweep."""
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

from scripts.nextgen_archetype_prior_terms_v1 import load_prior_terms
from scripts.nextgen_latent_codec_v1 import jaccard_text
from scripts.nextgen_verbatim_spine_codec_v1 import (
    spine_packet_binary_bytes,
    verbatim_spine_decode,
    verbatim_spine_decode_binary,
    verbatim_spine_encode,
    verbatim_spine_packet_to_binary,
)
from scripts.run_nextgen_hybrid_spine_logos_stack_v1 import _salience_reconstruct_logos

GOLDEN_BENCH = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
B2B_BENCH = (
    ROOT / "experiments/nextgen_clean_slate_cpu_v1/NEXTGEN_B2B_SPINE_BENCH_INPUT_V1.json"
)
SALIENCE_HOOK = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_salience_hook_only.json"
)
NAV_FRAME = ROOT / "experiments/nextgen_clean_slate_cpu_v1/ARCHETYPE_PRIOR_NAV_FRAME_V1.json"
LOGOS_PACK = ROOT / "docs/final/artifacts/logos_graphrag_bridge_evidence_pack_v1_latest.json"
OUT_DEFAULT = ROOT / "reports/ng40_path_a_keep_ratio_microgrid_v1_latest.json"
DEFAULT_RATIOS = (0.78, 0.82, 0.85, 0.88, 0.90, 0.92)
CANONICAL_KEEP = 0.88
MIN_SIDECAR_J = 0.75


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_cases(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    return list(doc.get("compression_cases") or [])


def _eval_cohort(
    cases: list[dict[str, Any]],
    keep_ratio: float,
    logos_terms: frozenset[str],
) -> dict[str, Any]:
    total_raw = total_spine_bin = total_sidecar = 0
    exact = 0
    j_side = 0.0
    n = len(cases)
    for c in cases:
        raw = str(c.get("raw_text") or "")
        pkt = verbatim_spine_encode(raw)
        blob = verbatim_spine_packet_to_binary(pkt)
        recon = verbatim_spine_decode_binary(blob)
        ok = raw == recon
        exact += int(ok)
        side, _ = _salience_reconstruct_logos(raw, keep_ratio, logos_terms)
        rb = len(raw.encode("utf-8"))
        sb = len(blob)
        sc = len(side.encode("utf-8"))
        total_raw += rb
        total_spine_bin += sb
        total_sidecar += sc
        j_side += jaccard_text(raw, side)

    parity = round(exact / n, 6) if n else 0.0
    combined = total_spine_bin + total_sidecar
    return {
        "case_count": n,
        "byte_exact_subset_parity": parity,
        "contract_met": exact == n and n > 0,
        "global_token_saving_rate_spine_binary_only": round(
            1.0 - (total_spine_bin / max(1, total_raw)), 6
        ),
        "global_token_saving_rate_spine_plus_sidecar_billable": round(
            1.0 - (combined / max(1, total_raw)), 6
        ),
        "avg_logos_sidecar_jaccard": round(j_side / max(1, n), 6),
    }


def _pick_knees(rows: list[dict[str, Any]], *, saving_key: str) -> dict[str, Any]:
    ok_rows = [
        r
        for r in rows
        if r.get("contract_met")
        and (r.get("avg_logos_sidecar_jaccard") or 0) >= MIN_SIDECAR_J
    ]
    if not ok_rows:
        ok_rows = [r for r in rows if r.get("contract_met")] or rows

    j_best = max(ok_rows, key=lambda r: float(r.get("avg_logos_sidecar_jaccard") or 0))
    s_best = max(ok_rows, key=lambda r: float(r.get(saving_key) or -999))

    canonical = next((r for r in rows if r.get("keep_ratio") == CANONICAL_KEEP), None)
    return {
        "knee_j_first": {
            "keep_ratio": j_best.get("keep_ratio"),
            "avg_logos_sidecar_jaccard": j_best.get("avg_logos_sidecar_jaccard"),
            "billable_saving": j_best.get(saving_key),
        },
        "knee_saving_first": {
            "keep_ratio": s_best.get("keep_ratio"),
            "avg_logos_sidecar_jaccard": s_best.get("avg_logos_sidecar_jaccard"),
            "billable_saving": s_best.get(saving_key),
        },
        "canonical_0_88": canonical,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--golden-bench", type=Path, default=GOLDEN_BENCH)
    ap.add_argument("--b2b-bench", type=Path, default=B2B_BENCH)
    ap.add_argument("--output", type=Path, default=OUT_DEFAULT)
    ap.add_argument(
        "--keep-ratios",
        nargs="*",
        type=float,
        default=list(DEFAULT_RATIOS),
    )
    ap.add_argument("--min-sidecar-j", type=float, default=MIN_SIDECAR_J)
    args = ap.parse_args(argv)

    if not args.golden_bench.is_file():
        print(json.dumps({"error": "missing_golden_bench"}), file=sys.stderr)
        return 2

    prior_terms, prior_meta = load_prior_terms(
        root=ROOT,
        salience_hook_path=SALIENCE_HOOK,
        nav_frame_path=NAV_FRAME,
        logos_pack_path=LOGOS_PACK,
        max_terms=128,
    )
    logos_terms = frozenset(prior_terms)
    golden_cases = _load_cases(args.golden_bench)
    b2b_cases = _load_cases(args.b2b_bench)

    golden_rows: list[dict[str, Any]] = []
    b2b_rows: list[dict[str, Any]] = []
    for kr in args.keep_ratios:
        g = _eval_cohort(golden_cases, kr, logos_terms)
        golden_rows.append({"keep_ratio": kr, **g})
        if b2b_cases:
            b = _eval_cohort(b2b_cases, kr, logos_terms)
            b2b_rows.append({"keep_ratio": kr, **b})

    golden_knees = _pick_knees(
        golden_rows, saving_key="global_token_saving_rate_spine_plus_sidecar_billable"
    )
    b2b_knees = (
        _pick_knees(
            b2b_rows, saving_key="global_token_saving_rate_spine_plus_sidecar_billable"
        )
        if b2b_rows
        else None
    )

    b2b_spine_only = None
    if b2b_rows:
        b2b_spine_only = b2b_rows[0].get("global_token_saving_rate_spine_binary_only")

    suggested_keep = CANONICAL_KEEP
    if b2b_knees and b2b_knees.get("knee_j_first", {}).get("keep_ratio") is not None:
        suggested_keep = float(b2b_knees["knee_j_first"]["keep_ratio"])
    elif golden_knees.get("knee_j_first", {}).get("keep_ratio") is not None:
        suggested_keep = float(golden_knees["knee_j_first"]["keep_ratio"])

    doc = {
        "schema": "ng40_path_a_keep_ratio_microgrid_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "track_a_active_write": False,
        "send_gate": "HOLD",
        "decode_contract_ko": "official_recon = verbatim_spine_decode_binary(MKVS); sidecar = preview/billable adjunct",
        "thresholds": {
            "min_sidecar_jaccard_for_saving_knee": args.min_sidecar_j,
            "canonical_keep_ratio": CANONICAL_KEEP,
        },
        "prior_terms_count": len(logos_terms),
        "prior_terms_meta": prior_meta,
        "sources": {
            "golden_bench": str(args.golden_bench.relative_to(ROOT)).replace("\\", "/"),
            "b2b_bench": str(args.b2b_bench.relative_to(ROOT)).replace("\\", "/")
            if b2b_cases
            else None,
        },
        "golden40": {
            "sweep": golden_rows,
            "knees": golden_knees,
        },
        "b2b_longform": {
            "sweep": b2b_rows,
            "knees": b2b_knees,
        }
        if b2b_rows
        else {"note": "b2b bench missing — run build_nextgen_longform_spine_bench_input_v1.py"},
        "recommendation": {
            "product_headline_kpi": "b2b_longform spine_binary_only (~22.3% on longform cohort)",
            "b2b_spine_binary_only_constant": b2b_spine_only,
            "sidecar_role": "NON_GATING preview — tune keep_ratio for sidecar_j only",
            "suggested_keep_ratio": suggested_keep,
            "suggested_keep_rationale_ko": "knee_j_first on B2B longform; spine saving invariant to keep_ratio",
            "apply_forbidden": True,
        },
        "reproducible_command": (
            "py scripts/run_ng40_path_a_keep_ratio_microgrid_v1.py"
        ),
        "forbidden": [
            "merge b2b billable saving with MULTILENS_ULTRA_COMPRESSION_ACTIVE 47%",
            "sidecar_jaccard as official recon quality",
        ],
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    b2b_best = None
    if b2b_rows:
        b2b_best = b2b_knees["knee_saving_first"]["billable_saving"] if b2b_knees else None

    print(
        json.dumps(
            {
                "ok": True,
                "output": str(args.output),
                "grid_points": len(golden_rows),
                "b2b_best_billable_saving": b2b_best,
                "suggested_keep_ratio": suggested_keep,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
