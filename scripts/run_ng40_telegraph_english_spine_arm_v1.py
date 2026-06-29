#!/usr/bin/env python3
"""[HYPO] Golden-40 Telegraph-English spine prestage arm — honest B-track codec bench."""
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
from scripts.nextgen_telegraph_english_prestage_v1 import (
    telegraph_char_saving_rate,
    telegraph_prestage,
)
from scripts.nextgen_verbatim_spine_codec_v1 import (
    spine_packet_json_bytes,
    verbatim_spine_decode,
    verbatim_spine_encode,
)

BENCH = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
ACTIVE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
OUT_DEFAULT = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_telegraph_english_spine_arm_v1_latest.json"
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


def _run_arm(cases: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    prestage_save_sum = 0.0
    spine_store = 0
    raw_bytes = 0
    j_sum = 0.0
    min_j = 1.0
    for c in cases:
        raw = str(c.get("raw_text") or "")
        prestaged, sidecar = telegraph_prestage(raw)
        pkt = verbatim_spine_encode(prestaged)
        recon = verbatim_spine_decode(pkt)
        jac = jaccard_text(raw, recon)
        j_sum += jac
        min_j = min(min_j, jac)
        rb = len(raw.encode("utf-8"))
        raw_bytes += rb
        spine_store += spine_packet_json_bytes(pkt)
        prestage_save_sum += telegraph_char_saving_rate(raw, prestaged)
        rows.append(
            {
                "id": c.get("id"),
                "prestage_saving_rate": telegraph_char_saving_rate(raw, prestaged),
                "spine_stored_bytes": spine_packet_json_bytes(pkt),
                "reconstruction_fidelity_jaccard": round(jac, 6),
                "sidecar": sidecar,
            }
        )
    n = len(rows)
    agg = {
        "case_count": n,
        "avg_prestage_saving_rate": round(prestage_save_sum / max(1, n), 6),
        "global_token_saving_rate": round(1.0 - (spine_store / max(1, raw_bytes)), 6),
        "avg_reconstruction_fidelity_jaccard": round(j_sum / max(1, n), 6),
        "min_reconstruction_fidelity_jaccard": round(min_j, 6),
        "decode_contract": "verbatim_spine_decode(prestaged); jaccard vs original raw",
    }
    return agg, rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bench-input", type=Path, default=BENCH)
    ap.add_argument("--out-json", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()
    if not args.bench_input.is_file():
        print(json.dumps({"error": "missing_bench", "path": str(args.bench_input)}))
        return 2

    doc = json.loads(args.bench_input.read_text(encoding="utf-8-sig"))
    cases = list(doc.get("compression_cases") or [])
    frozen = _frozen()
    agg, rows = _run_arm(cases)

    out = {
        "schema": "ng40_telegraph_english_spine_arm_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "track_a_active_write": False,
        "send_gate": "HOLD",
        "apply_forbidden": True,
        "arm_id": "telegraph_english_spine_prestage_v1",
        "paper_pointer": "arXiv:2605.04426 (external claim; MKM honest prestage only)",
        "bench_input": str(args.bench_input.relative_to(ROOT)).replace("\\", "/"),
        "frozen_baseline": frozen,
        "aggregate": agg,
        "beat_check": _beat(agg, frozen),
        "case_sample": rows[:5],
        "guardrails": [
            "Not RAGDocumentPrestageTokenizer or TelegraphEnglishSymbolicCompressor",
            "Does not write ACTIVE or MS headline",
            "Separate codec arm vs latent token-delete",
        ],
        "reproducible_command": "py scripts/run_ng40_telegraph_english_spine_arm_v1.py",
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "wrote": str(args.out_json),
                "beat_frozen": out["beat_check"].get("beat_frozen"),
                "saving": agg.get("global_token_saving_rate"),
                "jaccard": agg.get("avg_reconstruction_fidelity_jaccard"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
