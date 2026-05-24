#!/usr/bin/env python3
"""COMP-ATOM-02: tokenizer strategy comparison for genesis pointer on V2 bench (research)."""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.core.master_codebook_lexicon_v1_bridge import unicode_word_tokens  # noqa: E402
from scripts.mkm_inter_agent_ko_tokenization_v1 import tokenize as ko_tokenize  # noqa: E402
from scripts.pointer_hash_snapping_router_v1 import _build_lexicon, _read_json  # noqa: E402

PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"
INPUTS = PILOT / "comp_atom02_router_inputs_full40_v1.json"
CODEBOOK = PILOT / "genesis_gematria_4d_codebook_lexicon_seed_v1.json"

_PUNCT_TAIL = re.compile(r"^(.+?)([.,!?;:]+)$")


def _tok_whitespace(text: str) -> list[str]:
    return [t for t in text.strip().split() if t]


def _tok_unicode_word(text: str) -> list[str]:
    return sorted(unicode_word_tokens(text))


def _tok_unicode_word_ordered(text: str) -> list[str]:
    return [t.lower() for t in re.findall(r"\w+", text, flags=re.UNICODE) if t]


def _tok_strip_punct_ws(text: str) -> list[str]:
    out: list[str] = []
    for raw in _tok_whitespace(text):
        t = raw
        m = _PUNCT_TAIL.match(t)
        if m:
            t = m.group(1)
        if t:
            out.append(t.lower() if t.isascii() else t)
    return out


def _tok_ko_word(text: str) -> list[str]:
    return ko_tokenize(text, mode="word")


def _candidate_ok(text: str, lexicon_terms: set[str], tokenize: Callable[[str], list[str]]) -> tuple[bool, list[str]]:
    toks = tokenize(text)
    unresolved = [t for t in toks if t not in lexicon_terms and t.lower() not in lexicon_terms]
    # also try lower match for latin
    fixed_unresolved = []
    for t in unresolved:
        tl = t.lower()
        if tl in lexicon_terms or t in lexicon_terms:
            continue
        fixed_unresolved.append(t)
    return len(toks) > 0 and len(fixed_unresolved) == 0, fixed_unresolved


def main() -> int:
    texts = json.loads(INPUTS.read_text(encoding="utf-8"))
    lexicon = set(_build_lexicon(_read_json(CODEBOOK)).keys())
    # case-insensitive alias for ascii terms in codebook
    for k in list(lexicon):
        if k.isascii():
            lexicon.add(k.lower())

    strategies: dict[str, Callable[[str], list[str]]] = {
        "whitespace_router_default": _tok_whitespace,
        "unicode_word_ordered": _tok_unicode_word_ordered,
        "strip_punct_whitespace": _tok_strip_punct_ws,
        "ko_inter_agent_word": _tok_ko_word,
    }

    results: dict[str, dict] = {}
    for name, fn in strategies.items():
        ok = 0
        oov: Counter[str] = Counter()
        per = []
        for text in texts:
            good, unr = _candidate_ok(text, lexicon, fn)
            if good:
                ok += 1
            for u in unr:
                oov[u] += 1
            per.append({"ok": good, "unresolved_count": len(unr), "unresolved_sample": unr[:5]})
        results[name] = {
            "pointer_candidate_ok_count": ok,
            "pointer_candidate_ok_rate": round(ok / len(texts), 4) if texts else 0.0,
            "top_oov": oov.most_common(15),
            "per_case": per,
        }

    out = {
        "schema": "comp_atom02_ko_pointer_tokenizer_poc_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "research_only": True,
        "codebook_term_count": len(_build_lexicon(_read_json(CODEBOOK))),
        "case_count": len(texts),
        "strategies": results,
        "baseline_sentence_poc": "reports/constitution/btrack_pilot/comp_atom02_genesis_pointer_sentence_poc_v1.json",
        "note": (
            "Improved tokenization alone does not enable pointer_primary on bench until genesis "
            "codebook covers unicode_word token set (41k lexicon is separate path in evaluate_report)."
        ),
    }
    path = PILOT / "comp_atom02_ko_pointer_tokenizer_poc_v1.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = {k: v["pointer_candidate_ok_count"] for k, v in results.items()}
    print(json.dumps({"wrote": str(path), "ok_counts": summary}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
