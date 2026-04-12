# -*- coding: utf-8 -*-
"""Emit minimal sasang-tagged token lists for B-track 4-grid compression spike (not production)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.core.scm_boming_jiju_lexicon_v1 import DEFAULT_LEXICON_PATH, entries_by_constitution

SCHEMA = "myeongri_sasang_codebook_spike_v1"
SASANG_KEYS = ("taeeum_in", "soeum_in", "taeyang_in", "soyang_in")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--out-dir",
        type=Path,
        default=_ROOT / "docs" / "final" / "artifacts" / "derived" / "myeongri_sasang_codebook_spike_v1",
    )
    ap.add_argument("--lexicon", type=Path, default=DEFAULT_LEXICON_PATH)
    args = ap.parse_args()

    grouped = entries_by_constitution(args.lexicon)
    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    global_terms: list[str] = []
    seen: set[str] = set()
    for key in SASANG_KEYS:
        for e in grouped.get(key, []):
            t = str(e.get("term", "")).strip()
            if t and t not in seen:
                seen.add(t)
                global_terms.append(t)

    for key in SASANG_KEYS:
        terms = sorted(
            {str(e.get("term", "")).strip() for e in grouped.get(key, []) if str(e.get("term", "")).strip()},
            key=len,
            reverse=True,
        )
        (out_dir / f"{key}.json").write_text(
            json.dumps(
                {
                    "schema": SCHEMA,
                    "sasang_constitution": key,
                    "tokens": terms,
                    "hypothesis_tier": "B",
                    "boundary_ack": True,
                    "label": "[HYPO][NON-MEDICAL] Spike codebook from scm_boming_jiju_lexicon_v1",
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    (out_dir / "global_tokens.json").write_text(
        json.dumps(
            {
                "schema": SCHEMA,
                "role": "global_union",
                "tokens": sorted(global_terms, key=len, reverse=True),
                "hypothesis_tier": "B",
                "boundary_ack": True,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    def _rel(p: Path) -> str:
        try:
            return str(p.resolve().relative_to(_ROOT.resolve()))
        except ValueError:
            return str(p)

    meta = {
        "schema": SCHEMA + "_meta",
        "lexicon_source": _rel(args.lexicon),
        "per_constitution_counts": {k: len(grouped.get(k, [])) for k in SASANG_KEYS},
        "global_unique_terms": len(global_terms),
        "out_dir": _rel(out_dir),
    }
    (out_dir / "codebook_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
