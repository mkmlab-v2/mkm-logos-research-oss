#!/usr/bin/env python3
"""[HYPO] P2b: salience latent PoC on Golden-40 (replaces CRC stub for shadow evidence).

Not neural E2E — greedy salience retention + optional target_saving sweep.
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

BENCH_INPUT = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
ACTIVE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
DEFAULT_OUT = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_latent_poc_v1_latest.json"
)

# Token keep ratio (aligned with stub keep_percent ~0.82 → ~20% saving / ~0.82 jaccard)
DEFAULT_SWEEP = (0.72, 0.74, 0.76, 0.78, 0.80, 0.82, 0.84, 0.86)
# Extended grid for B-track PoC exploration (step 0.02)
DEFAULT_SWEEP_EXTENDED = tuple(round(i / 100, 2) for i in range(68, 93, 2))


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _frozen_metrics() -> dict[str, Any]:
    if not ACTIVE.is_file():
        return {"present": False}
    doc = json.loads(ACTIVE.read_text(encoding="utf-8"))
    cm = doc.get("compression_metrics") or {}
    return {
        "present": True,
        "global_token_saving_rate": cm.get("global_token_saving_rate"),
        "avg_reconstruction_fidelity_jaccard": cm.get("avg_reconstruction_fidelity_jaccard"),
    }


def _beat_check(candidate: dict, frozen: dict) -> dict[str, Any]:
    if not frozen.get("present"):
        return {"beat_frozen": False, "reason": "missing_frozen"}
    saving_c = candidate.get("global_token_saving_rate")
    jacc_c = candidate.get("avg_reconstruction_fidelity_jaccard")
    saving_f = frozen.get("global_token_saving_rate")
    jacc_f = frozen.get("avg_reconstruction_fidelity_jaccard")
    if None in (saving_c, jacc_c, saving_f, jacc_f):
        return {"beat_frozen": False, "reason": "incomplete_metrics"}
    beat = float(saving_c) >= float(saving_f) and float(jacc_c) >= float(jacc_f)
    return {
        "beat_frozen": beat,
        "delta_saving_pp": round((float(saving_c) - float(saving_f)) * 100, 2),
        "delta_jaccard_pp": round((float(jacc_c) - float(jacc_f)) * 100, 2),
        "reason": "both_saving_and_jaccard_gte_frozen" if beat else "not_both_axes",
    }


def _eval_cases(
    cases_in: list[dict[str, Any]],
    keep_ratio: float,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    total_raw = 0
    total_comp = 0
    jacc_sum = 0.0
    for c in cases_in:
        raw = str(c.get("raw_text") or "")
        comp, recon = latent_salience_reconstruct(raw, keep_ratio)
        raw_len = max(1, len(raw))
        comp_len = len(comp)
        saving = 1.0 - (comp_len / raw_len)
        jac = jaccard_text(raw, recon)
        rows.append(
            {
                "id": c.get("id"),
                "raw_chars": len(raw),
                "compressed_chars": comp_len,
                "keep_ratio": keep_ratio,
                "token_saving_rate": round(saving, 6),
                "reconstruction_fidelity_jaccard": round(jac, 6),
            }
        )
        total_raw += raw_len
        total_comp += comp_len
        jacc_sum += jac
    n = len(rows)
    aggregate = {
        "case_count": n,
        "global_token_saving_rate": round(1.0 - (total_comp / max(1, total_raw)), 6),
        "avg_reconstruction_fidelity_jaccard": round(jacc_sum / max(1, n), 6),
    }
    return aggregate, rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bench-input", type=Path, default=BENCH_INPUT)
    ap.add_argument(
        "--keep-ratio",
        type=float,
        default=None,
        help="Fraction of token instances to keep (0-1)",
    )
    ap.add_argument(
        "--sweep",
        nargs="*",
        type=float,
        default=None,
        help="Sweep keep_ratio values (default grid)",
    )
    ap.add_argument("--no-sweep", action="store_true", help="Use single --keep-ratio 0.80")
    ap.add_argument(
        "--extended-sweep",
        action="store_true",
        help=f"Use extended keep_ratio grid ({len(DEFAULT_SWEEP_EXTENDED)} steps, 0.68–0.92)",
    )
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.bench_input.is_file():
        print(f"error: missing {args.bench_input}", file=sys.stderr)
        return 1

    doc_in = json.loads(args.bench_input.read_text(encoding="utf-8"))
    cases_in = doc_in.get("compression_cases") or []
    if not cases_in:
        print("error: no compression_cases", file=sys.stderr)
        return 1

    frozen = _frozen_metrics()
    sweep_vals: list[float]
    if args.no_sweep or args.keep_ratio is not None:
        sweep_vals = [float(args.keep_ratio if args.keep_ratio is not None else 0.80)]
    elif args.sweep:
        sweep_vals = list(args.sweep)
    elif args.extended_sweep:
        sweep_vals = list(DEFAULT_SWEEP_EXTENDED)
    else:
        sweep_vals = list(DEFAULT_SWEEP)

    sweep_rows: list[dict[str, Any]] = []
    for ts in sweep_vals:
        agg, _per = _eval_cases(cases_in, ts)
        sweep_rows.append(
            {
                "keep_ratio": ts,
                "aggregate": agg,
                "beat_check": _beat_check(agg, frozen),
            }
        )

    def _rank(r: dict[str, Any]) -> tuple:
        bc = r.get("beat_check") or {}
        agg = r.get("aggregate") or {}
        return (
            1 if bc.get("beat_frozen") else 0,
            float(agg.get("avg_reconstruction_fidelity_jaccard") or 0),
            float(agg.get("global_token_saving_rate") or 0),
        )

    sweep_rows.sort(key=_rank, reverse=True)
    best_sweep = sweep_rows[0]
    best_kr = float(best_sweep["keep_ratio"])
    aggregate, per_case = _eval_cases(cases_in, best_kr)

    doc = {
        "schema": "nextgen_latent_poc_ng40_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "track_a_active_write": False,
        "golden40_compatible": True,
        "implementation_phase": "p2_latent_salience_poc_v1",
        "bench_input": str(args.bench_input.relative_to(ROOT)).replace("\\", "/"),
        "poc_params": {
            "algorithm": "greedy_salience_token_retention_v1",
            "must_keep_anchors": list({"사상의학", "체질", "sasang", "myeongri", "bible"}),
            "note": "Not neural E2E; improves over CRC stub via salience ordering",
        },
        "selected_keep_ratio": best_kr,
        "sweep": sweep_rows,
        "aggregate": aggregate,
        "frozen_baseline_parallel": frozen,
        "beat_check": _beat_check(aggregate, frozen),
        "per_case": per_case,
        "guardrails": [
            "No Track A active write",
            "Do not claim 41k abolished or Jaccard eliminated",
            "Human sign-off + 41k parity before ACTIVE overwrite",
        ],
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "wrote": str(args.out_json),
                "selected_keep_ratio": best_kr,
                "beat_frozen": doc["beat_check"]["beat_frozen"],
                "saving": aggregate.get("global_token_saving_rate"),
                "jaccard": aggregate.get("avg_reconstruction_fidelity_jaccard"),
                "sweep_any_beat": any(
                    (r.get("beat_check") or {}).get("beat_frozen") for r in sweep_rows
                ),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
