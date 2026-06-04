#!/usr/bin/env python3
"""[HYPO] P2: latent indexer stub on Golden-40 cases (shadow vs frozen Track A).

Not a production compressor — deterministic token-retention stub for B-track evidence.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import zlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
BENCH_INPUT = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
ACTIVE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
DEFAULT_OUT = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_latent_stub_shadow_v1_latest.json"
)

WORD_RE = re.compile(r"[A-Za-z0-9_가-힣]+")


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _norm_words(text: str) -> set[str]:
    return set(WORD_RE.findall(text.lower()))


def _jaccard(a: str, b: str) -> float:
    sa, sb = _norm_words(a), _norm_words(b)
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def _stub_latent_reconstruct(raw: str, keep_percent: int) -> tuple[str, str]:
    """Return (compressed_stub, reconstructed_stub) from raw text."""
    tokens = WORD_RE.findall(raw)
    if not tokens:
        return "", ""
    kept: list[str] = []
    for tok in tokens:
        bucket = zlib.crc32(tok.lower().encode("utf-8")) % 100
        if bucket < keep_percent:
            kept.append(tok)
    if not kept:
        kept = [tokens[0]]
    compressed = " ".join(kept)
    reconstructed = compressed
    return compressed, reconstructed


def _frozen_metrics() -> dict[str, Any]:
    if not ACTIVE.is_file():
        return {"present": False}
    doc = json.loads(ACTIVE.read_text(encoding="utf-8"))
    cm = doc.get("compression_metrics") or {}
    return {
        "present": True,
        "global_token_saving_rate": cm.get("global_token_saving_rate"),
        "avg_reconstruction_fidelity_jaccard": cm.get("avg_reconstruction_fidelity_jaccard"),
        "alignment_pass_rate_raw": cm.get("alignment_pass_rate_raw"),
        "alignment_pass_rate_repair_v2": cm.get("alignment_pass_rate_repair_v2")
        or cm.get("alignment_pass_rate"),
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
    beat = saving_c >= saving_f and jacc_c >= jacc_f
    return {
        "beat_frozen": beat,
        "delta_saving_pp": round((saving_c - saving_f) * 100, 2),
        "delta_jaccard_pp": round((jacc_c - jacc_f) * 100, 2),
        "reason": "both_saving_and_jaccard_gte_frozen" if beat else "not_both_axes",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--bench-input",
        type=Path,
        default=BENCH_INPUT,
        help="Golden-40 eval input JSON",
    )
    ap.add_argument(
        "--keep-percent",
        type=int,
        default=82,
        help="Deterministic token keep ratio 0-100 (stub latent coverage)",
    )
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.bench_input.is_file():
        print(f"error: missing bench input: {args.bench_input}", file=sys.stderr)
        return 1
    keep = max(1, min(99, int(args.keep_percent)))

    doc_in = json.loads(args.bench_input.read_text(encoding="utf-8"))
    cases_in = doc_in.get("compression_cases") or []
    if not cases_in:
        print("error: no compression_cases", file=sys.stderr)
        return 1

    rows: list[dict[str, Any]] = []
    total_raw = 0
    total_comp = 0
    jacc_sum = 0.0

    for c in cases_in:
        raw = str(c.get("raw_text") or "")
        comp_stub, recon_stub = _stub_latent_reconstruct(raw, keep)
        raw_len = max(1, len(raw))
        comp_len = len(comp_stub)
        saving = 1.0 - (comp_len / raw_len)
        jac = _jaccard(raw, recon_stub)
        rows.append(
            {
                "id": c.get("id"),
                "raw_chars": len(raw),
                "stub_compressed_chars": comp_len,
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
        "avg_reconstruction_fidelity_jaccard": round(jacc_sum / n, 6),
    }
    frozen = _frozen_metrics()
    doc = {
        "schema": "nextgen_latent_stub_ng40_shadow_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "track_a_active_write": False,
        "golden40_compatible": True,
        "implementation_phase": "p2_latent_stub_v0",
        "bench_input": str(args.bench_input.relative_to(ROOT)).replace("\\", "/"),
        "stub_params": {
            "keep_percent": keep,
            "algorithm": "deterministic_crc32_token_retention",
            "note": "Not neural E2E; shadow for charter DOD only",
        },
        "aggregate": aggregate,
        "frozen_baseline_parallel": frozen,
        "beat_check": _beat_check(aggregate, frozen),
        "per_case": rows,
        "guardrails": [
            "No Track A active write",
            "No claim Jaccard eliminated",
            "Human sign-off required before ACTIVE overwrite",
        ],
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "wrote": str(args.out_json),
                "case_count": n,
                "beat_frozen": doc["beat_check"]["beat_frozen"],
                "avg_jaccard": aggregate["avg_reconstruction_fidelity_jaccard"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
