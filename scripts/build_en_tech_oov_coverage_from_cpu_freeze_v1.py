#!/usr/bin/env python3
"""P2: en_tech lane OOV / lexicon coverage vs CPU frozen sweep (research_only)."""
from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.core.master_codebook_lexicon_v1_bridge import (  # noqa: E402
    lexicon_hits_for_text,
    resolve_latest_codebook_path,
    unicode_word_tokens,
)

LANE_ID = "en_tech_spec_stress_v1"
MATRIX = ROOT / "docs/final/artifacts/UNIVERSAL_COMPRESSION_BENCH_MATRIX_INPUT_V1.json"
FROZEN_SWEEP = (
    ROOT
    / "reports/constitution/btrack_pilot/baselines/router_tuning_v1"
    / "comp_universal_bench_matrix_sweep_cpu_literal_hybrid_full1103_frozen.json"
)
FREEZE_MANIFEST = (
    ROOT
    / "reports/constitution/btrack_pilot/baselines/router_tuning_v1"
    / "cpu_universal_matrix_literal_hybrid_freeze_manifest_v1.json"
)
OUT = ROOT / "reports/constitution/btrack_pilot/comp_en_tech_oov_coverage_from_cpu_freeze_v1.json"
FORBIDDEN = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _frozen_metrics_by_case(sweep: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in sweep.get("rows") or sweep.get("per_case_results") or []:
        cid = str(row.get("case_id") or "")
        if not cid:
            continue
        wire = row.get("economy_plus_wire") or row.get("economy") or {}
        out[cid] = {
            "compression_profile": row.get("compression_profile"),
            "global_token_saving_rate": wire.get("global_token_saving_rate"),
            "avg_reconstruction_fidelity_jaccard": wire.get("avg_reconstruction_fidelity_jaccard"),
        }
    return out


def main() -> int:
    cb = resolve_latest_codebook_path()
    if cb is None:
        print("ABORT: lexicon not found")
        return 1
    if not MATRIX.is_file() or not FROZEN_SWEEP.is_file() or not FREEZE_MANIFEST.is_file():
        print("ABORT: missing matrix / frozen sweep / manifest")
        return 1

    matrix = json.loads(MATRIX.read_text(encoding="utf-8-sig"))
    sweep = json.loads(FROZEN_SWEEP.read_text(encoding="utf-8-sig"))
    manifest = json.loads(FREEZE_MANIFEST.read_text(encoding="utf-8-sig"))
    frozen_by_case = _frozen_metrics_by_case(sweep)

    cases = [
        c
        for c in (matrix.get("compression_cases") or [])
        if str(c.get("lane_id") or "") == LANE_ID
    ]
    if not cases:
        print("ABORT: no en_tech cases in matrix input")
        return 1

    per_case: list[dict[str, Any]] = []
    miss_counter: Counter[str] = Counter()
    total_toks = 0
    total_hits = 0
    jaccards: list[float] = []

    for c in cases:
        cid = str(c.get("id") or "")
        raw = str(c.get("raw_text", ""))
        toks = unicode_word_tokens(raw)
        hits, _meta = lexicon_hits_for_text(raw, cb)
        missed = sorted(toks - {h.lower() for h in hits})
        for m in missed:
            miss_counter[m] += 1
        n_tok = len(toks)
        n_hit = len(hits)
        total_toks += n_tok
        total_hits += n_hit
        fr = frozen_by_case.get(cid, {})
        j = fr.get("avg_reconstruction_fidelity_jaccard")
        if isinstance(j, (int, float)):
            jaccards.append(float(j))
        per_case.append(
            {
                "case_id": cid,
                "token_count": n_tok,
                "lexicon_hit_count": n_hit,
                "miss_count": len(missed),
                "hit_ratio": round(n_hit / n_tok, 4) if n_tok else 0.0,
                "oov_ratio": round(len(missed) / n_tok, 4) if n_tok else 0.0,
                "hits_sample": sorted(hits)[:8],
                "miss_sample": missed[:12],
                "frozen_cpu_literal_hybrid": fr,
            }
        )

    headline = manifest.get("headline_metrics_1103") or {}
    out_doc = {
        "schema": "comp_en_tech_oov_coverage_from_cpu_freeze_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "lane_id": LANE_ID,
        "lexicon_path": str(cb.relative_to(ROOT)).replace("\\", "/"),
        "freeze_manifest": str(FREEZE_MANIFEST.relative_to(ROOT)).replace("\\", "/"),
        "frozen_sweep": str(FROZEN_SWEEP.relative_to(ROOT)).replace("\\", "/"),
        "case_count": len(cases),
        "aggregate": {
            "total_unicode_tokens": total_toks,
            "total_lexicon_hits": total_hits,
            "aggregate_hit_ratio": round(total_hits / total_toks, 4) if total_toks else 0.0,
            "aggregate_oov_ratio": round((total_toks - total_hits) / total_toks, 4) if total_toks else 0.0,
            "jaccard_mean_frozen_literal": round(sum(jaccards) / len(jaccards), 6) if jaccards else 0.0,
            "jaccard_min_frozen_literal": round(min(jaccards), 6) if jaccards else 0.0,
            "below_0_85_count": sum(1 for j in jaccards if j < 0.85),
        },
        "freeze_headline_cross_check": headline,
        "top_missing_tokens": [
            {"token": t, "case_frequency": n} for t, n in miss_counter.most_common(40)
        ],
        "per_case": per_case,
        "track_a_active_written": False,
        "forbidden_write_path": str(FORBIDDEN.relative_to(ROOT)).replace("\\", "/"),
        "interpretation": (
            "en_tech_spec_stress_v1 OOV under 41k lexicon correlates with frozen CPU literal-hybrid "
            "J floor ~0.76–0.77; GPU/semantic PoC is [HYPO] next — not Track A promotion."
        ),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "wrote": str(OUT.relative_to(ROOT)).replace("\\", "/"),
                "case_count": len(cases),
                "aggregate": out_doc["aggregate"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
