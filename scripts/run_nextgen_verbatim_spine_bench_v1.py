#!/usr/bin/env python3
"""[HYPO] Golden-40 verbatim spine bench — byte_exact 1.0 + spine saving metrics."""
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
from scripts.nextgen_verbatim_spine_codec_v1 import (
    char_saving_rate,
    spine_packet_json_bytes,
    verbatim_spine_decode,
    verbatim_spine_encode,
)

BENCH = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
ACTIVE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
OUT_DEFAULT = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_verbatim_spine_bench_v1_latest.json"
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _frozen() -> dict[str, Any]:
    if not ACTIVE.is_file():
        return {"present": False}
    cm = json.loads(ACTIVE.read_text(encoding="utf-8")).get("compression_metrics") or {}
    return {
        "present": True,
        "global_token_saving_rate": cm.get("global_token_saving_rate"),
        "avg_reconstruction_fidelity_jaccard": cm.get("avg_reconstruction_fidelity_jaccard"),
    }


def _beat(cand: dict, fr: dict) -> dict[str, Any]:
    if not fr.get("present"):
        return {"beat_frozen": False, "reason": "missing_frozen"}
    s_c, j_c = cand.get("global_token_saving_rate"), cand.get("avg_reconstruction_fidelity_jaccard")
    s_f, j_f = fr.get("global_token_saving_rate"), fr.get("avg_reconstruction_fidelity_jaccard")
    if None in (s_c, j_c, s_f, j_f):
        return {"beat_frozen": False, "reason": "incomplete_metrics"}
    beat = float(s_c) >= float(s_f) and float(j_c) >= float(j_f)
    return {
        "beat_frozen": beat,
        "delta_saving_pp": round((float(s_c) - float(s_f)) * 100, 2),
        "delta_jaccard_pp": round((float(j_c) - float(j_f)) * 100, 2),
        "reason": "both_saving_and_jaccard_gte_frozen" if beat else "not_both_axes",
    }


def _run_spine_only(cases: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    total_raw = 0
    total_store = 0
    exact = 0
    j_sum = 0.0
    for c in cases:
        raw = str(c.get("raw_text") or "")
        pkt = verbatim_spine_encode(raw)
        recon = verbatim_spine_decode(pkt)
        store = spine_packet_json_bytes(pkt)
        ok = raw == recon
        exact += int(ok)
        jac = jaccard_text(raw, recon)
        j_sum += jac
        raw_b = len(raw.encode("utf-8"))
        total_raw += raw_b
        total_store += store
        rows.append(
            {
                "id": c.get("id"),
                "byte_exact": ok,
                "spine_codec": pkt.get("codec"),
                "stored_bytes": store,
                "reconstruction_fidelity_jaccard": round(jac, 6),
            }
        )
    n = len(rows)
    agg = {
        "case_count": n,
        "byte_exact_count": exact,
        "byte_exact_subset_parity": round(exact / n, 6) if n else 0.0,
        "global_token_saving_rate": round(1.0 - (total_store / max(1, total_raw)), 6),
        "avg_reconstruction_fidelity_jaccard": round(j_sum / max(1, n), 6),
    }
    return agg, rows


def _run_hybrid(
    cases: list[dict[str, Any]],
    keep_ratio: float,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Recon always from spine; salience channel is sidecar metrics only."""
    rows: list[dict[str, Any]] = []
    total_raw = 0
    total_spine = 0
    total_sidecar = 0
    exact = 0
    j_sum = 0.0
    sem_j_sum = 0.0
    for c in cases:
        raw = str(c.get("raw_text") or "")
        pkt = verbatim_spine_encode(raw)
        recon = verbatim_spine_decode(pkt)
        ok = raw == recon
        exact += int(ok)
        _, sem_preview = latent_salience_reconstruct(raw, keep_ratio)
        spine_b = spine_packet_json_bytes(pkt)
        sidecar_b = len(sem_preview.encode("utf-8"))
        total_raw += len(raw.encode("utf-8"))
        total_spine += spine_b
        total_sidecar += sidecar_b
        j_sum += jaccard_text(raw, recon)
        sem_j_sum += jaccard_text(raw, sem_preview)
        rows.append(
            {
                "id": c.get("id"),
                "byte_exact": ok,
                "keep_ratio": keep_ratio,
                "spine_stored_bytes": spine_b,
                "semantic_sidecar_bytes": sidecar_b,
                "reconstruction_fidelity_jaccard": round(jaccard_text(raw, recon), 6),
                "semantic_preview_jaccard": round(jaccard_text(raw, sem_preview), 6),
            }
        )
    n = len(rows)
    combined_store = total_spine + total_sidecar
    agg = {
        "case_count": n,
        "byte_exact_count": exact,
        "byte_exact_subset_parity": round(exact / n, 6) if n else 0.0,
        "global_token_saving_rate_spine_only": round(
            1.0 - (total_spine / max(1, total_raw)), 6
        ),
        "global_token_saving_rate_spine_plus_sidecar": round(
            1.0 - (combined_store / max(1, total_raw)), 6
        ),
        "global_token_saving_rate": round(
            1.0 - (combined_store / max(1, total_raw)), 6
        ),
        "avg_reconstruction_fidelity_jaccard": round(j_sum / max(1, n), 6),
        "avg_semantic_preview_jaccard": round(sem_j_sum / max(1, n), 6),
        "decode_contract": "recon=verbatim_spine_decode only",
    }
    return agg, rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bench-input", type=Path, default=BENCH)
    ap.add_argument("--out-json", type=Path, default=OUT_DEFAULT)
    ap.add_argument(
        "--mode",
        choices=("spine_only", "hybrid"),
        default="spine_only",
    )
    ap.add_argument("--keep-ratio", type=float, default=0.82)
    ap.add_argument(
        "--hybrid-sweep",
        nargs="*",
        type=float,
        default=None,
        help="If set with --mode hybrid, sweep keep_ratio values",
    )
    args = ap.parse_args()
    if not args.bench_input.is_file():
        print(json.dumps({"error": "missing_bench", "path": str(args.bench_input)}))
        return 2

    doc = json.loads(args.bench_input.read_text(encoding="utf-8-sig"))
    cases = list(doc.get("compression_cases") or [])
    frozen = _frozen()
    arms: list[dict[str, Any]] = []

    if args.mode == "spine_only":
        agg, rows = _run_spine_only(cases)
        arms.append(
            {
                "arm_id": "verbatim_spine_only_v1",
                "aggregate": agg,
                "beat_check": _beat(agg, frozen),
                "case_sample": rows[:5],
            }
        )
    else:
        ratios = args.hybrid_sweep or [args.keep_ratio]
        for kr in ratios:
            agg, rows = _run_hybrid(cases, float(kr))
            arms.append(
                {
                    "arm_id": f"hybrid_spine_plus_salience_{kr:.2f}",
                    "keep_ratio": kr,
                    "aggregate": agg,
                    "beat_check": _beat(agg, frozen),
                    "case_sample": rows[:3],
                }
            )

    out = {
        "schema": "nextgen_verbatim_spine_bench_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "track_a_active_write": False,
        "use_master_codebook_lexicon_v1": False,
        "mode": args.mode,
        "bench_input": str(args.bench_input.relative_to(ROOT)).replace("\\", "/"),
        "frozen_baseline": frozen,
        "arms": arms,
        "guardrails": [
            "byte_exact from spine decode; semantic sidecar does not alter recon",
            "Does not write ACTIVE or MS headline",
        ],
        "spec_pointer": (
            "experiments/nextgen_clean_slate_cpu_v1/VERBATIM_SPINE_EXACT_RESTORE_SPEC_V1.json"
        ),
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    best = arms[0]["aggregate"] if arms else {}
    print(
        json.dumps(
            {
                "wrote": str(args.out_json),
                "byte_exact_parity": best.get("byte_exact_subset_parity"),
                "spine_saving": best.get("global_token_saving_rate")
                or best.get("global_token_saving_rate_spine_only"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
