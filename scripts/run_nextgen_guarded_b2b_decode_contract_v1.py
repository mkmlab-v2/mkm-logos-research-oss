#!/usr/bin/env python3
"""[HYPO] B2B guarded decode contract: spine decode = official recon (byte_exact); sidecar metrics only."""
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
from scripts.nextgen_latent_codec_v1 import jaccard_text, latent_salience_reconstruct
from scripts.nextgen_verbatim_spine_codec_v1 import (
    verbatim_spine_decode,
    verbatim_spine_encode,
)
from scripts.run_nextgen_hybrid_spine_logos_stack_v1 import _salience_reconstruct_logos

BENCH = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
SALIENCE_HOOK = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_salience_hook_only.json"
)
NAV_FRAME = (
    ROOT / "experiments/nextgen_clean_slate_cpu_v1/ARCHETYPE_PRIOR_NAV_FRAME_V1.json"
)
OUT_DEFAULT = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_guarded_b2b_decode_contract_v1_latest.json"
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bench-input", type=Path, default=BENCH)
    ap.add_argument("--out-json", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--keep-ratio", type=float, default=0.82)
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

    rows: list[dict[str, Any]] = []
    exact = 0
    j_b2b = j_side = j_latent = 0.0
    total_raw = total_spine = 0

    for c in cases:
        raw = str(c.get("raw_text") or "")
        pkt = verbatim_spine_encode(raw)
        b2b_recon = verbatim_spine_decode(pkt)
        ok = raw == b2b_recon
        exact += int(ok)
        side, _ = _salience_reconstruct_logos(raw, args.keep_ratio, prior_terms)
        _, latent_preview = latent_salience_reconstruct(raw, args.keep_ratio)
        rb = len(raw.encode("utf-8"))
        sb = len(json.dumps(pkt, ensure_ascii=False).encode("utf-8"))
        total_raw += rb
        total_spine += sb
        j_b2b += jaccard_text(raw, b2b_recon)
        j_side += jaccard_text(raw, side)
        j_latent += jaccard_text(raw, latent_preview)
        rows.append(
            {
                "id": c.get("id"),
                "byte_exact": ok,
                "b2b_recon_source": "verbatim_spine_decode",
                "sidecar_jaccard": round(jaccard_text(raw, side), 6),
                "latent_preview_jaccard": round(jaccard_text(raw, latent_preview), 6),
            }
        )

    n = len(rows)
    out = {
        "schema": "nextgen_guarded_b2b_decode_contract_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "track_a_active_write": False,
        "gating_policy": "NON_GATING",
        "decode_contract_ko": "B2B 공식 복원 = verbatim spine only; sidecar/latent preview는 메트릭 전용",
        "keep_ratio": args.keep_ratio,
        "prior_terms_count": len(prior_terms),
        "prior_terms_meta": prior_meta,
        "aggregate": {
            "case_count": n,
            "byte_exact_count": exact,
            "byte_exact_subset_parity": round(exact / n, 6) if n else 0.0,
            "contract_met": exact == n,
            "global_token_saving_rate_spine_storage": round(
                1.0 - (total_spine / max(1, total_raw)), 6
            ),
            "avg_b2b_recon_jaccard": round(j_b2b / max(1, n), 6),
            "avg_sidecar_preview_jaccard": round(j_side / max(1, n), 6),
            "avg_latent_preview_jaccard": round(j_latent / max(1, n), 6),
        },
        "case_sample": rows[:6],
        "guardrails": [
            "Does not claim latent path byte_exact",
            "Does not write ACTIVE or trigger live trading",
        ],
        "spec_pointer": (
            "experiments/nextgen_clean_slate_cpu_v1/VERBATIM_SPINE_EXACT_RESTORE_SPEC_V1.json"
        ),
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "wrote": str(args.out_json),
                "byte_exact_parity": out["aggregate"]["byte_exact_subset_parity"],
                "contract_met": out["aggregate"]["contract_met"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
