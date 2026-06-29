#!/usr/bin/env python3
"""[HYPO] Step 1: minimize prior-driven residual sidecar bytes at semantic preview floor."""
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
    spine_packet_body_bytes,
    spine_packet_json_bytes,
    verbatim_spine_decode,
    verbatim_spine_encode,
)
from scripts.run_nextgen_hybrid_spine_logos_stack_v1 import _salience_reconstruct_logos

BENCH = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
ACTIVE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
SALIENCE_HOOK = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_salience_hook_only.json"
)
NAV_FRAME = (
    ROOT / "experiments/nextgen_clean_slate_cpu_v1/ARCHETYPE_PRIOR_NAV_FRAME_V1.json"
)
OUT_DEFAULT = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_prior_residual_diet_v1_latest.json"
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _frozen_saving() -> float | None:
    if not ACTIVE.is_file():
        return None
    cm = json.loads(ACTIVE.read_text(encoding="utf-8")).get("compression_metrics") or {}
    return float(cm.get("global_token_saving_rate", 0))


def _eval_keep(
    cases: list[dict[str, Any]],
    keep_ratio: float,
    prior_terms: frozenset[str],
    *,
    sidecar_billable: bool,
) -> dict[str, Any]:
    total_raw = total_spine_json = total_spine_body = total_sidecar = 0
    exact = 0
    j_side = 0.0
    for c in cases:
        raw = str(c.get("raw_text") or "")
        pkt = verbatim_spine_encode(raw)
        recon = verbatim_spine_decode(pkt)
        exact += int(raw == recon)
        sem, _ = _salience_reconstruct_logos(raw, keep_ratio, prior_terms)
        rb = len(raw.encode("utf-8"))
        sb_json = spine_packet_json_bytes(pkt)
        sb_body = spine_packet_body_bytes(pkt)
        sc_b = len(sem.encode("utf-8"))
        total_raw += rb
        total_spine_json += sb_json
        total_spine_body += sb_body
        total_sidecar += sc_b
        j_side += jaccard_text(raw, sem)

    n = max(1, len(cases))
    billable = total_spine_json + (total_sidecar if sidecar_billable else 0)
    return {
        "keep_ratio": round(keep_ratio, 4),
        "sidecar_billable": sidecar_billable,
        "byte_exact_subset_parity": round(exact / max(1, len(cases)), 6),
        "avg_sidecar_preview_jaccard": round(j_side / n, 6),
        "total_sidecar_bytes": total_sidecar,
        "avg_sidecar_bytes_per_case": round(total_sidecar / n, 2),
        "global_token_saving_rate_spine_json_only": round(
            1.0 - (total_spine_json / max(1, total_raw)), 6
        ),
        "global_token_saving_rate_spine_body_only": round(
            1.0 - (total_spine_body / max(1, total_raw)), 6
        ),
        "global_token_saving_rate_billable_payload": round(
            1.0 - (billable / max(1, total_raw)), 6
        ),
    }


def _pick_diet_row(
    grid: list[dict[str, Any]],
    semantic_floor: float,
) -> dict[str, Any] | None:
    ok = [r for r in grid if r["avg_sidecar_preview_jaccard"] >= semantic_floor]
    if not ok:
        return None
    return min(ok, key=lambda r: (r["total_sidecar_bytes"], r["keep_ratio"]))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bench-input", type=Path, default=BENCH)
    ap.add_argument("--out-json", type=Path, default=OUT_DEFAULT)
    ap.add_argument(
        "--semantic-floor",
        type=float,
        default=0.871,
        help="Min avg sidecar preview Jaccard (NON_GATING metric)",
    )
    ap.add_argument(
        "--keep-grid-step",
        type=float,
        default=0.04,
        help="Grid step from 0.08 to 0.92",
    )
    args = ap.parse_args()
    if not args.bench_input.is_file():
        print(json.dumps({"error": "missing_bench"}))
        return 2

    prior_terms, prior_meta = load_prior_terms(
        root=ROOT,
        salience_hook_path=SALIENCE_HOOK,
        nav_frame_path=NAV_FRAME,
        logos_pack_path=None,
        max_terms=128,
    )
    cases = json.loads(args.bench_input.read_text(encoding="utf-8-sig")).get(
        "compression_cases"
    ) or []

    step = max(0.02, args.keep_grid_step)
    ratios = [round(0.08 + i * step, 4) for i in range(int((0.92 - 0.08) / step) + 1)]
    grid_bill: list[dict[str, Any]] = []
    grid_free: list[dict[str, Any]] = []
    for kr in ratios:
        grid_bill.append(_eval_keep(cases, kr, prior_terms, sidecar_billable=True))
        grid_free.append(_eval_keep(cases, kr, prior_terms, sidecar_billable=False))

    diet_bill = _pick_diet_row(grid_bill, args.semantic_floor)
    diet_free = _pick_diet_row(grid_free, args.semantic_floor)
    fr = _frozen_saving()

    out = {
        "schema": "nextgen_prior_residual_diet_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "track_a_active_write": False,
        "semantic_preview_floor": args.semantic_floor,
        "prior_terms_count": len(prior_terms),
        "prior_terms_meta": prior_meta,
        "frozen_track_a_saving_reference": fr,
        "billing_modes": {
            "spine_json_plus_sidecar": "billable = spine JSON + residual sidecar bytes",
            "spine_json_zero_sidecar_bill": "billable = spine JSON only; sidecar preview free",
            "spine_body_reference": "design reference: zlib/raw body without JSON envelope",
        },
        "grid_sidecar_billable": grid_bill,
        "grid_sidecar_zero_bill": grid_free,
        "recommended_diet": {
            "sidecar_billable": diet_bill,
            "sidecar_zero_bill": diet_free,
        },
        "promotion_note_ko": (
            "Track A 47.5%는 multilens codec arm; NG spine JSON은 Golden-40 짧문에서 "
            "과금 payload beat 불가할 수 있음 — dual_axis는 billing_mode별 분리 보고"
        ),
        "guardrails": [
            "Official recon remains verbatim_spine_decode only",
            "Does not write ACTIVE",
        ],
    }
    if diet_free and fr is not None:
        out["beat_frozen_on_zero_bill_spine_json"] = (
            diet_free["global_token_saving_rate_spine_json_only"] >= fr
        )
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "wrote": str(args.out_json),
                "diet_zero_bill_keep": (diet_free or {}).get("keep_ratio"),
                "diet_billable_keep": (diet_bill or {}).get("keep_ratio"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
