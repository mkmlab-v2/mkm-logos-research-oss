#!/usr/bin/env python3
"""COMP-ATOM-02: full bench∩41k lexicon → genesis codebook + pointer OK rate (research)."""
from __future__ import annotations

import json
import re
import subprocess
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
from scripts.pointer_hash_snapping_router_v1 import (  # noqa: E402
    _build_lexicon,
    _read_json,
    _route_one,
)

PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"
INPUT_V2 = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
SHADOW = PILOT / "genesis_pointer_runtime_shadow_only_v1.json"
CODEBOOK_OUT = PILOT / "genesis_gematria_4d_codebook_bench_lexicon_full_v1.json"
TERMS_OUT = PILOT / "comp_atom02_bench_lexicon_full_terms_v1.json"
ROUTER_OUT = PILOT / "comp_atom02_pointer_router_bench_lexicon_full_v1.json"

_PUNCT_TAIL = re.compile(r"^(.+?)([.,!?;:]+)$")


def _tok_unicode_ordered(text: str) -> list[str]:
    return [t.lower() for t in re.findall(r"\w+", text, flags=re.UNICODE) if t]


def _tok_strip_punct(text: str) -> list[str]:
    out: list[str] = []
    for t in _tok_unicode_ordered(text):
        m = _PUNCT_TAIL.match(t)
        out.append(m.group(1) if m else t)
    return out


def _collect_bench_lexicon_terms(cases: list[dict], lex_path: Path) -> list[str]:
    forms = set()
    doc = json.loads(lex_path.read_text(encoding="utf-8"))
    for ent in doc.get("entries") or []:
        nf = ent.get("normalized_form")
        if isinstance(nf, str) and nf.strip():
            forms.add(nf.strip().lower())

    terms: set[str] = set()
    for c in cases:
        toks = unicode_word_tokens(str(c.get("raw_text", "")))
        terms |= {t for t in toks if t in forms and len(t) >= 2}
    return sorted(terms)


def _per_case_coverage(cases: list[dict], vocab: set[str]) -> list[dict]:
    rows = []
    for c in cases:
        toks = _tok_strip_punct(str(c.get("raw_text", "")))
        unr = [t for t in toks if t not in vocab and t.lower() not in vocab]
        rows.append(
            {
                "id": c.get("id"),
                "token_count": len(toks),
                "all_in_vocab": len(toks) > 0 and len(unr) == 0,
                "unresolved_count": len(unr),
                "unresolved_sample": unr[:8],
            }
        )
    return rows


def main() -> int:
    lex_path = resolve_latest_codebook_path()
    if lex_path is None:
        print("ABORT: lexicon missing")
        return 1

    inp = json.loads(INPUT_V2.read_text(encoding="utf-8"))
    cases = inp.get("compression_cases") or []
    terms = _collect_bench_lexicon_terms(cases, lex_path)
    TERMS_OUT.write_text(json.dumps(terms, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/build_genesis_gematria_4d_codebook_v1.py"),
            "--terms-json",
            str(TERMS_OUT),
            "--out",
            str(CODEBOOK_OUT),
        ],
        check=True,
        cwd=str(ROOT),
    )

    texts = [str(c.get("raw_text", "")) for c in cases if c.get("raw_text")]
    inputs_path = PILOT / "comp_atom02_router_inputs_full40_v1.json"
    inputs_path.write_text(json.dumps(texts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/pointer_hash_snapping_router_v1.py"),
            "--runtime-config",
            str(SHADOW),
            "--codebook-json",
            str(CODEBOOK_OUT),
            "--inputs-json",
            str(inputs_path),
            "--enable-snap",
            "--out",
            str(ROUTER_OUT),
        ],
        check=True,
        cwd=str(ROOT),
    )

    router_doc = json.loads(ROUTER_OUT.read_text(encoding="utf-8"))
    ws_ok = router_doc.get("summary", {}).get("pointer_candidate_ok_count", 0)

    lexicon = _build_lexicon(_read_json(CODEBOOK_OUT))
    vocab = set(lexicon.keys()) | {k.lower() for k in lexicon if k.isascii()}
    runtime = _read_json(SHADOW)
    uw_ok = 0
    for text in texts:
        toks = _tok_strip_punct(text)
        unr = [t for t in toks if t not in vocab and t.lower() not in vocab]
        if len(toks) > 0 and not unr:
            uw_ok += 1

    per_case = _per_case_coverage(cases, vocab)
    case_ok = sum(1 for r in per_case if r["all_in_vocab"])

    out = {
        "schema": "comp_atom02_expanded_lexicon_codebook_poc_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "research_only": True,
        "term_count": len(terms),
        "codebook": str(CODEBOOK_OUT.relative_to(ROOT)).replace("\\", "/"),
        "pointer_whitespace_router_ok": ws_ok,
        "pointer_unicode_strip_punct_ok": uw_ok,
        "per_case_all_tokens_in_vocab": case_ok,
        "per_case": per_case,
        "prior_74_term_codebook_ok": 0,
        "note": (
            "Expanded codebook = all bench unicode_word tokens hitting 41k lexicon. "
            "Router CLI still uses whitespace split; unicode_strip_punct column is research routing."
        ),
    }
    path = PILOT / "comp_atom02_expanded_lexicon_codebook_poc_v1.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": path.name, "terms": len(terms), "ws_ok": ws_ok, "uw_ok": uw_ok, "case_ok": case_ok}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
