#!/usr/bin/env python3
"""[HYPO] Intersect CJK bigrams from IJEOMA chunk lane with master codebook forms."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHUNK_LANE = ROOT / "docs/final/artifacts/universal_compression_bench_lane_ijeoma_chunk_table_v1.json"
OUT = ROOT / "reports/constitution/btrack_pilot/comp_hanja_phrase_lexicon_hypo_slice_v1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    import sys

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts.core.master_codebook_lexicon_v1_bridge import (
        _load_normalized_forms,
        cjk_bigram_tokens,
        resolve_latest_codebook_path,
    )

    ap = argparse.ArgumentParser()
    ap.add_argument("--lane-json", type=Path, default=CHUNK_LANE)
    ap.add_argument("--max-cases", type=int, default=0, help="0 = all cases in lane")
    ap.add_argument("--out-json", type=Path, default=OUT)
    ap.add_argument(
        "--lexicon-json",
        type=Path,
        default=ROOT / "reports/constitution/btrack_pilot/ijeoma_hanja_codebook_lexicon_v1_hypo_latest.json",
    )
    args = ap.parse_args()

    lane_path = (ROOT / args.lane_json).resolve() if not args.lane_json.is_absolute() else args.lane_json
    out_path = (ROOT / args.out_json).resolve() if not args.out_json.is_absolute() else args.out_json
    doc = json.loads(lane_path.read_text(encoding="utf-8"))
    cases = list(doc.get("compression_cases") or [])
    if args.max_cases > 0:
        cases = cases[: args.max_cases]

    lex_arg = (ROOT / args.lexicon_json).resolve() if not args.lexicon_json.is_absolute() else args.lexicon_json
    lex_path = lex_arg if lex_arg.is_file() else resolve_latest_codebook_path()
    forms = (
        _load_normalized_forms(str(lex_path.resolve()))
        if lex_path and lex_path.is_file()
        else frozenset()
    )
    phrase_forms = {f for f in forms if len(f) >= 2}

    bigrams: set[str] = set()
    for case in cases:
        bigrams |= cjk_bigram_tokens(str(case.get("raw_text") or ""))

    matched = sorted(bigrams & phrase_forms)
    out = {
        "schema": "comp_hanja_phrase_lexicon_hypo_slice_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "lane": str(lane_path.relative_to(ROOT)).replace("\\", "/"),
        "cases_scanned": len(cases),
        "bigram_candidates": len(bigrams),
        "phrase_forms_in_lexicon": len(phrase_forms),
        "matched_phrase_count": len(matched),
        "matched_phrases_sample": matched[:80],
        "lexicon_path": str(lex_path) if lex_path else None,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"wrote": out_path.name, "matched_phrase_count": len(matched)},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
