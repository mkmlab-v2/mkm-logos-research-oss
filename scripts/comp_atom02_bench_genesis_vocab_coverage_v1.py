#!/usr/bin/env python3
"""Bench token vocabulary vs genesis 74-term codebook coverage (research)."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.core.master_codebook_lexicon_v1_bridge import (  # noqa: E402
    resolve_latest_codebook_path,
    unicode_word_tokens,
)
from scripts.pointer_hash_snapping_router_v1 import _build_lexicon, _read_json  # noqa: E402

PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"
INPUT_V2 = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
CODEBOOK = PILOT / "genesis_gematria_4d_codebook_lexicon_seed_v1.json"


def main() -> int:
    src = json.loads(INPUT_V2.read_text(encoding="utf-8"))
    bench_tokens: set[str] = set()
    for c in src.get("compression_cases") or []:
        bench_tokens |= unicode_word_tokens(str(c.get("raw_text", "")))

    genesis = set(_build_lexicon(_read_json(CODEBOOK)).keys())
    cb = resolve_latest_codebook_path()
    lexicon_forms: set[str] = set()
    if cb:
        doc = json.loads(cb.read_text(encoding="utf-8"))
        for ent in doc.get("entries") or []:
            nf = ent.get("normalized_form")
            if isinstance(nf, str):
                lexicon_forms.add(nf.strip().lower())

    g_hit = bench_tokens & genesis
    g_hit_ci = {t for t in bench_tokens if t in genesis or t.lower() in {k.lower() for k in genesis}}
    l_hit = bench_tokens & lexicon_forms

    out = {
        "schema": "comp_atom02_bench_genesis_vocab_coverage_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "research_only": True,
        "bench_unique_tokens": len(bench_tokens),
        "genesis_codebook_terms": len(genesis),
        "lexicon_normalized_forms": len(lexicon_forms),
        "bench_in_genesis_exact": len(g_hit),
        "bench_in_genesis_case_insensitive": len(g_hit_ci),
        "bench_in_41k_lexicon": len(l_hit),
        "bench_oov_vs_genesis_sample": sorted(bench_tokens - genesis)[:30],
        "interpretation": (
            f"Pointer needs all tokens in sentence; bench has {len(bench_tokens)} unique tokens "
            f"but genesis only covers {len(g_hit_ci)} — tokenizer normalization cannot fix vocabulary gap."
        ),
    }
    path = PILOT / "comp_atom02_bench_genesis_vocab_coverage_v1.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(path), "bench": len(bench_tokens), "in_genesis": len(g_hit_ci), "in_41k": len(l_hit)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
