#!/usr/bin/env python3
"""[HYPO] Scan hanja token coverage in master_codebook vs IJEOMA chunk lane — diagnostic only."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CHUNK_LANE = ROOT / "docs/final/artifacts/universal_compression_bench_lane_ijeoma_chunk_table_v1.json"
OUT = ROOT / "reports/constitution/btrack_pilot/comp_hanja_codebook_coverage_hypo_scan_v1.json"

_HANJA_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _hanja_chars(text: str) -> list[str]:
    return _HANJA_RE.findall(text)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lane-json", type=Path, default=CHUNK_LANE)
    ap.add_argument("--max-cases", type=int, default=30)
    ap.add_argument("--out-json", type=Path, default=OUT)
    args = ap.parse_args()

    from scripts.core.master_codebook_lexicon_v1_bridge import (
        _load_normalized_forms,
        lexicon_hits_for_text,
        resolve_latest_codebook_path,
    )

    lane_path = (ROOT / args.lane_json).resolve() if not args.lane_json.is_absolute() else args.lane_json
    out_path = (ROOT / args.out_json).resolve() if not args.out_json.is_absolute() else args.out_json
    doc = json.loads(lane_path.read_text(encoding="utf-8"))
    cases = (doc.get("compression_cases") or [])[: max(1, args.max_cases)]

    lex_path = resolve_latest_codebook_path()
    forms = _load_normalized_forms(str(lex_path.resolve())) if lex_path and lex_path.is_file() else frozenset()
    single_char_forms = {f for f in forms if len(f) == 1}

    char_counter: Counter[str] = Counter()
    eval_hit_counts_min2: list[int] = []
    eval_hit_counts_min1: list[int] = []
    for case in cases:
        text = str(case.get("raw_text") or "")
        char_counter.update(_hanja_chars(text))
        if lex_path:
            _, meta2 = lexicon_hits_for_text(text, lex_path, min_token_len=2)
            _, meta1 = lexicon_hits_for_text(text, lex_path, min_token_len=1)
            eval_hit_counts_min2.append(int(meta2.get("hit_count") or 0))
            eval_hit_counts_min1.append(int(meta1.get("hit_count") or 0))

    unique = set(char_counter.keys())
    char_hits = {c for c in unique if c.lower() in forms}
    char_hit_rate = len(char_hits) / len(unique) if unique else 0.0

    out = {
        "schema": "comp_hanja_codebook_coverage_hypo_scan_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "boundary_ack": "Does not change economy eval or Track A; probes why chunk lane hit_count=0.",
        "lane": str(lane_path.relative_to(ROOT)).replace("\\", "/"),
        "cases_sampled": len(cases),
        "lexicon": {
            "path": str(lex_path) if lex_path else None,
            "lexicon_term_count": len(forms),
            "single_char_normalized_forms": len(single_char_forms),
        },
        "hanja_unique_chars": len(unique),
        "hanja_char_hits_in_lexicon": len(char_hits),
        "hanja_char_hit_rate": round(char_hit_rate, 4),
        "eval_lexicon_hits_per_case": {
            "min_token_len_2": {
                "mean": round(sum(eval_hit_counts_min2) / len(eval_hit_counts_min2), 2)
                if eval_hit_counts_min2
                else 0,
                "max": max(eval_hit_counts_min2) if eval_hit_counts_min2 else 0,
            },
            "min_token_len_1": {
                "mean": round(sum(eval_hit_counts_min1) / len(eval_hit_counts_min1), 2)
                if eval_hit_counts_min1
                else 0,
                "max": max(eval_hit_counts_min1) if eval_hit_counts_min1 else 0,
            },
        },
        "root_cause_hint": (
            "lexicon_hits_for_text uses unicode_word_tokens; min_token_len>=2 skips single hanja "
            "→ hit_count=0 on chunk lane unless min_token_len=1 or phrase/bigram lexicon overlap."
        ),
        "top_chars_sample": char_counter.most_common(20),
        "miss_sample": sorted(unique - char_hits)[:30],
        "next_hypo": [
            "Export 수세보원/Corpus01 hanja phrases into master_codebook slice (lexicon CJK coverage ~0)",
            "cjk_bigram tokenization alone insufficient until normalized_form overlap exists",
            "Chunk lane remains coverage-only for matrix KPI until dedicated hanja codebook lands",
        ],
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": out_path.name, "hit_rate": out["hanja_char_hit_rate"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
