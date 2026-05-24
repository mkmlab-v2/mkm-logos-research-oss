#!/usr/bin/env python3
"""M18a: Compare KO tokenization modes vs 41k lexicon on health corpus."""

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

DEFAULT_OUT = ROOT / "docs/final/artifacts/mkm_inter_agent_ko_tokenization_experiment_v1_latest.json"

from scripts.run_mkm_inter_agent_dialogue_mock_v1 import ALPHA_LINES_HEALTH, BETA_LINES_HEALTH  # noqa: E402
from scripts.mkm_inter_agent_ko_tokenization_v1 import TokenizationMode, tokenize  # noqa: E402


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _hit_rate(text: str, path: Path, mode: TokenizationMode) -> dict[str, Any]:
    from scripts.core.master_codebook_lexicon_v1_bridge import _load_lexicon_index

    forms, _ = _load_lexicon_index(str(path.resolve()))
    toks = tokenize(text, mode)
    unique = list(dict.fromkeys(toks))
    hits = [t for t in unique if t.lower() in forms or t in forms]
    return {
        "token_count": len(unique),
        "hit_count": len(hits),
        "hit_rate": round(len(hits) / len(unique), 6) if unique else None,
    }


def run_experiment() -> dict[str, Any]:
    from scripts.core.master_codebook_lexicon_v1_bridge import resolve_latest_codebook_path

    path = resolve_latest_codebook_path()
    if path is None:
        return {"ok": False, "error": "lexicon_path_missing"}

    lines = ALPHA_LINES_HEALTH + BETA_LINES_HEALTH
    modes: list[TokenizationMode] = ["word", "hangul_syllable", "hangul_char"]
    by_mode: dict[str, Any] = {}

    for mode in modes:
        per_line = [_hit_rate(text, path, mode) for text in lines]
        total_t = sum(r["token_count"] for r in per_line)
        total_h = sum(r["hit_count"] for r in per_line)
        by_mode[mode] = {
            "lines": per_line,
            "aggregate_hit_rate": round(total_h / total_t, 6) if total_t else None,
            "aggregate_token_count": total_t,
            "aggregate_hit_count": total_h,
        }

    return {
        "ok": True,
        "schema": "mkm_inter_agent_ko_tokenization_experiment_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "corpus_line_count": len(lines),
        "lexicon_path": str(path.resolve()),
        "modes": by_mode,
        "note": "Hangul modes increase token granularity; main 41k lexicon has 0 hangul forms (M17).",
        "boundary_ack": "Tokenization experiment only; not production tokenizer change.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    doc = run_experiment()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc.get("ok"), "output": str(args.output)}, ensure_ascii=False))
    return 0 if doc.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
