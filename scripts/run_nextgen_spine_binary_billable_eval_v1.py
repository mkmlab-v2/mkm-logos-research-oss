#!/usr/bin/env python3
"""[HYPO] Golden-40 eval arm: MKVS binary spine billable bytes + byte_exact gate."""
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

from scripts.nextgen_latent_codec_v1 import jaccard_text
from scripts.nextgen_verbatim_spine_codec_v1 import (
    spine_packet_binary_bytes,
    spine_packet_json_bytes,
    verbatim_spine_decode,
    verbatim_spine_decode_binary,
    verbatim_spine_encode,
    verbatim_spine_packet_to_binary,
)

BENCH = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
ACTIVE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
OUT_DEFAULT = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_spine_binary_billable_eval_v1_latest.json"
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _frozen() -> dict[str, float]:
    if not ACTIVE.is_file():
        return {}
    cm = json.loads(ACTIVE.read_text(encoding="utf-8")).get("compression_metrics") or {}
    return {
        "global_token_saving_rate": float(cm.get("global_token_saving_rate") or 0),
        "avg_reconstruction_fidelity_jaccard": float(
            cm.get("avg_reconstruction_fidelity_jaccard") or 0
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bench-input", type=Path, default=BENCH)
    ap.add_argument("--out-json", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--arm-id", default="ng40_spine_binary_billable_v1")
    ap.add_argument("--bench-label", default="golden40")
    args = ap.parse_args()
    bench_input = args.bench_input if args.bench_input.is_absolute() else ROOT / args.bench_input
    bench_input = bench_input.resolve()
    out_json = args.out_json if args.out_json.is_absolute() else ROOT / args.out_json
    if not bench_input.is_file():
        print(json.dumps({"error": "missing_bench"}))
        return 2

    cases = json.loads(bench_input.read_text(encoding="utf-8-sig")).get(
        "compression_cases"
    ) or []
    total_raw = total_bin = total_json = 0
    exact = 0
    j_sum = 0.0
    rows: list[dict[str, Any]] = []

    for c in cases:
        raw = str(c.get("raw_text") or "")
        pkt = verbatim_spine_encode(raw)
        blob = verbatim_spine_packet_to_binary(pkt)
        recon = verbatim_spine_decode_binary(blob)
        ok = raw == recon
        exact += int(ok)
        rb = len(raw.encode("utf-8"))
        bb = len(blob)
        jb = spine_packet_json_bytes(pkt)
        total_raw += rb
        total_bin += bb
        total_json += jb
        j_sum += jaccard_text(raw, recon)
        rows.append(
            {
                "id": c.get("id"),
                "byte_exact": ok,
                "raw_utf8_bytes": rb,
                "spine_binary_bytes": bb,
                "spine_json_bytes": jb,
                "spine_codec": pkt.get("codec"),
            }
        )

    n = max(1, len(cases))
    saving_bin = round(1.0 - (total_bin / max(1, total_raw)), 6)
    saving_json = round(1.0 - (total_json / max(1, total_raw)), 6)
    parity = round(exact / max(1, len(cases)), 6)
    fr = _frozen()
    beat_bin = fr and saving_bin >= fr["global_token_saving_rate"]
    dual_axis = parity >= 1.0 and beat_bin

    agg = {
        "case_count": len(cases),
        "byte_exact_count": exact,
        "byte_exact_subset_parity": parity,
        "global_token_saving_rate": saving_bin,
        "avg_reconstruction_fidelity_jaccard": round(j_sum / n, 6),
        "global_token_saving_rate_spine_json_legacy": saving_json,
        "global_token_saving_rate_spine_binary_billable": saving_bin,
        "beat_frozen_saving_binary": beat_bin,
        "dual_axis_beat_binary_vs_frozen": dual_axis,
    }

    bench_rel = str(bench_input.relative_to(ROOT.resolve())).replace("\\", "/")
    out = {
        "schema": "ng40_spine_binary_billable_eval_v1",
        "arm_id": args.arm_id,
        "bench_label": args.bench_label,
        "bench_input": bench_rel,
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "track_a_active_write": False,
        "active_auto_merge": False,
        "gating_policy": "NON_GATING",
        "spec_pointer": (
            "experiments/nextgen_clean_slate_cpu_v1/"
            "VERBATIM_SPINE_BINARY_BILLABLE_SPEC_V1.json"
        ),
        "decode_contract_ko": "official_recon = verbatim_spine_decode_binary(MKVS)",
        "aggregate": agg,
        "compression_metrics": {
            "global_token_saving_rate": saving_bin,
            "avg_reconstruction_fidelity_jaccard": agg[
                "avg_reconstruction_fidelity_jaccard"
            ],
        },
        "frozen_reference": fr,
        "case_sample": rows[:6],
        "guardrails": [
            "Separate eval arm; does not overwrite MULTILENS_ULTRA_COMPRESSION_ACTIVE",
            "Sidecar/prior not included in billable bytes",
        ],
    }
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "wrote": str(out_json),
                "byte_exact_subset_parity": parity,
                "global_token_saving_rate": saving_bin,
                "dual_axis_beat": dual_axis,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
