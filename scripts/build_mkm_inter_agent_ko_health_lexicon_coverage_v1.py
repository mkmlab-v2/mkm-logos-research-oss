#!/usr/bin/env python3
"""M17a: Korean health dialogue corpus vs 41k lexicon coverage spike (measurement only)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_OUT = ROOT / "docs/final/artifacts/mkm_inter_agent_ko_health_lexicon_coverage_v1_latest.json"

from scripts.run_mkm_inter_agent_dialogue_mock_v1 import (  # noqa: E402
    ALPHA_LINES_HEALTH,
    BETA_LINES_HEALTH,
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _is_hangul(ch: str) -> bool:
    if not ch:
        return False
    o = ord(ch)
    return 0xAC00 <= o <= 0xD7A3 or 0x1100 <= o <= 0x11FF or 0x3130 <= o <= 0x318F


def analyze_line(text: str, path: Path) -> dict[str, Any]:
    from scripts.core.master_codebook_lexicon_v1_bridge import (
        lexicon_atom_sequence_for_text,
        lexicon_hits_for_text,
        unicode_word_tokens,
    )

    toks = unicode_word_tokens(text)
    hits, hit_meta = lexicon_hits_for_text(text, path)
    seq, seq_meta = lexicon_atom_sequence_for_text(text, path)
    hangul_tokens = [t for t in toks if any(_is_hangul(c) for c in t)]
    hangul_hits = [t for t in hangul_tokens if t in hits]
    return {
        "char_len": len(text),
        "token_count": len(toks),
        "lexicon_hit_count": len(hits),
        "atom_id_count": len(seq),
        "hit_rate_tokens": round(len(hits) / len(toks), 6) if toks else None,
        "atom_rate_tokens": round(len(seq) / len(toks), 6) if toks else None,
        "hangul_token_count": len(hangul_tokens),
        "hangul_hit_count": len(hangul_hits),
        "hangul_hit_rate": round(len(hangul_hits) / len(hangul_tokens), 6) if hangul_tokens else None,
        "missed_tokens_sample": sorted(toks - hits)[:24],
        "hit_meta_status": hit_meta.get("status"),
        "seq_meta_status": seq_meta.get("status"),
    }


def run_coverage() -> dict[str, Any]:
    from scripts.core.master_codebook_lexicon_v1_bridge import (
        resolve_latest_codebook_path,
        unicode_word_tokens,
        _load_lexicon_index,
    )

    path = resolve_latest_codebook_path()
    if path is None:
        return {"ok": False, "error": "lexicon_path_missing"}

    forms, _ = _load_lexicon_index(str(path.resolve()))
    hangul_in_lexicon = sum(1 for f in forms if any(_is_hangul(c) for c in f))

    lines = ALPHA_LINES_HEALTH + BETA_LINES_HEALTH
    per_line = [analyze_line(text, path) for text in lines]
    all_toks: set[str] = set()
    all_hits: set[str] = set()
    for text in lines:
        from scripts.core.master_codebook_lexicon_v1_bridge import lexicon_hits_for_text

        toks = unicode_word_tokens(text)
        hits, _ = lexicon_hits_for_text(text, path)
        all_toks |= toks
        all_hits |= hits

    missed = sorted(all_toks - all_hits)
    return {
        "ok": True,
        "schema": "mkm_inter_agent_ko_health_lexicon_coverage_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "lexicon_path": str(path.resolve()),
        "lexicon_term_count": len(forms),
        "hangul_normalized_forms_in_lexicon": hangul_in_lexicon,
        "corpus_line_count": len(lines),
        "aggregate": {
            "token_count": len(all_toks),
            "lexicon_hit_count": len(all_hits),
            "hit_rate_tokens": round(len(all_hits) / len(all_toks), 6) if all_toks else None,
            "missed_token_count": len(missed),
            "missed_tokens_sample": missed[:40],
        },
        "lines": per_line,
        "hypothesis_note": (
            "[HYPO] Low health atom rate is expected when master_codebook normalized_form is "
            "predominantly Latin; this spike measures gap size only — not a lexicon expansion commit."
        ),
        "boundary_ack": "Measurement spike only; no production KO lexicon rollout or Track A claim.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    doc = run_coverage()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc.get("ok"), "output": str(args.output)}, ensure_ascii=False))
    return 0 if doc.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
