#!/usr/bin/env python3
"""41k lexicon lookup exception taxonomy — read-only audit on Golden-40 bench (B-track).

Does not write MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json or change bridge defaults.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.core.master_codebook_lexicon_v1_bridge import (  # noqa: E402
    cjk_bigram_tokens,
    lexicon_hits_for_text,
    resolve_latest_codebook_path,
    unicode_word_tokens,
)

INPUT_V2 = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
ANALYSIS = ROOT / "reports/constitution/btrack_pilot/comp_atom02_lexicon_must_keep_analysis_v1.json"
OUT = ROOT / "reports/lexicon_lookup_exception_audit_v1_latest.json"

# English function / stop tokens that inflate must_keep when present in 41k normalized_form.
FUNCTION_WORD_STOP = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "but",
        "can",
        "for",
        "from",
        "in",
        "is",
        "it",
        "not",
        "of",
        "on",
        "or",
        "so",
        "that",
        "the",
        "to",
        "while",
        "with",
    }
)

_HANGUL_RE = re.compile(r"[\uac00-\ud7a3]")


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _hangul_ratio(raw: str) -> float:
    if not raw:
        return 0.0
    h = len(_HANGUL_RE.findall(raw))
    return round(h / max(len(raw), 1), 4)


def _classify_case(
    case_id: str,
    raw: str,
    *,
    cb_path: Path,
    min_token_len: int = 2,
) -> dict:
    toks = unicode_word_tokens(raw)
    hits, meta = lexicon_hits_for_text(raw, cb_path, min_token_len=min_token_len)
    hits_cjk, meta_cjk = lexicon_hits_for_text(
        raw, cb_path, min_token_len=min_token_len, include_cjk_bigrams=True
    )
    short_filtered = {t for t in toks if len(t) < min_token_len}
    missed = sorted(t for t in toks if len(t) >= min_token_len and t not in hits)
    func_hits = sorted(h for h in hits if h in FUNCTION_WORD_STOP)
    hr = _hangul_ratio(raw)

    if meta.get("status") != "ok":
        bucket = "EXC_LEXICON_FILE_OR_SCHEMA"
    elif hr >= 0.15 and len(hits) == 0:
        bucket = "EXC_HANGUL_DOMINANT_ZERO_HIT"
    elif hr >= 0.15 and len(hits_cjk) > len(hits):
        bucket = "EXC_HANGUL_CJK_BIGRAM_PARTIAL"
    elif func_hits and len(func_hits) >= max(1, len(hits) // 2):
        bucket = "EXC_FUNCTION_WORD_MUST_KEEP_INFLATION"
    elif len(hits) == 0:
        bucket = "EXC_ZERO_HIT_LATIN_OR_MIXED"
    else:
        bucket = "EXC_OK_DOMAIN_TERM_HITS"

    return {
        "id": case_id,
        "exception_bucket": bucket,
        "hangul_char_ratio": hr,
        "token_count": len(toks),
        "lexicon_hit_count": len(hits),
        "lexicon_hit_count_with_cjk_bigrams": len(hits_cjk),
        "function_word_hits": func_hits[:12],
        "missed_tokens_sample": missed[:12],
        "short_tokens_filtered_count": len(short_filtered),
        "hits_sample": sorted(hits)[:8],
        "bridge_meta_status": meta.get("status"),
    }


def main() -> int:
    if not INPUT_V2.is_file():
        print(f"ABORT: missing {INPUT_V2}")
        return 1
    cb = resolve_latest_codebook_path()
    if cb is None:
        print("ABORT: lexicon path not resolved")
        return 1

    src = json.loads(INPUT_V2.read_text(encoding="utf-8"))
    cases = src.get("compression_cases") or []
    per = [_classify_case(str(c.get("id", "")), str(c.get("raw_text", "")), cb_path=cb) for c in cases]

    bucket_counts = Counter(r["exception_bucket"] for r in per)
    func_hit_global: Counter[str] = Counter()
    for row in per:
        for w in row.get("function_word_hits") or []:
            func_hit_global[w] += 1

    ablation = {}
    if ANALYSIS.is_file():
        ablation = json.loads(ANALYSIS.read_text(encoding="utf-8")).get("compression_ablation") or {}

    recommended = [
        {
            "priority": "P0",
            "action": "hangul_tokenizer_or_normalized_form",
            "scope": "cases cmp2_011–cmp2_040 (Hangul-dominant zero-hit)",
            "note": "Bridge uses \\w+ only; no Hangul syllable/bigram in default path. Pilot include_cjk_bigrams before must_keep merge.",
            "track": "b_track_research_only",
        },
        {
            "priority": "P1",
            "action": "function_word_must_keep_denylist",
            "scope": "English stop/function tokens in FUNCTION_WORD_STOP",
            "note": "Reduce false must_keep inflation on cmp2_001–010 without shrinking 41k row count.",
            "track": "b_track_research_only",
        },
        {
            "priority": "P2",
            "action": "pointer_ssot_refresh",
            "scope": "master_codebook_bench_lexicon_pointer_v1_latest.json",
            "note": "Run build_master_codebook_bench_lexicon_pointer_v1.py on lexicon export change only.",
            "track": "ops",
        },
    ]

    doc = {
        "schema": "lexicon_lookup_exception_audit_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "track_a_active_write": False,
        "lexicon_path": str(cb.relative_to(ROOT)).replace("\\", "/"),
        "bench_input": str(INPUT_V2.relative_to(ROOT)).replace("\\", "/"),
        "case_count": len(per),
        "bucket_counts": dict(bucket_counts),
        "function_word_hit_frequency": dict(func_hit_global.most_common(16)),
        "compression_ablation_pointer": str(ANALYSIS.relative_to(ROOT)).replace("\\", "/")
        if ANALYSIS.is_file()
        else None,
        "compression_ablation_delta_on_minus_off": (ablation.get("delta_on_minus_off") or {}),
        "taxonomy": {
            "EXC_HANGUL_DOMINANT_ZERO_HIT": "Hangul-heavy text; default \\w+ lookup yields 0 hits — must_keep not lexicon-augmented.",
            "EXC_HANGUL_CJK_BIGRAM_PARTIAL": "CJK bigram path adds hits vs default; policy not in Track A frozen profile.",
            "EXC_FUNCTION_WORD_MUST_KEEP_INFLATION": "High share of English function-word lexicon hits — saving↓ / Jaccard↑ risk.",
            "EXC_ZERO_HIT_LATIN_OR_MIXED": "Latin bench text with no lexicon intersection (unexpected; review tokens).",
            "EXC_OK_DOMAIN_TERM_HITS": "Expected domain/English content terms driving must_keep.",
            "EXC_LEXICON_FILE_OR_SCHEMA": "resolve_latest_codebook_path or schema failure.",
        },
        "per_case": per,
        "recommended_hardening": recommended,
        "guardrails": [
            "FAIL-COMP-004: do not overwrite MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json from this audit.",
            "Do not cite repair-only or 1103 matrix as Track A promotion proof.",
            "31k41k shadow chain unchanged — separate prophecy research rail.",
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "wrote": str(OUT),
                "bucket_counts": dict(bucket_counts),
                "top_function_words": func_hit_global.most_common(5),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
