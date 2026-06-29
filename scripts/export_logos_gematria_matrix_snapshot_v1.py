#!/usr/bin/env python3
"""Deterministic gematria 4D pairwise matrix snapshot [HYPO] — lookup layer only.

Reproducible:
  py scripts/export_logos_gematria_matrix_snapshot_v1.py
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from myeongni.gematria_myeongri_math_v1 import cosine_similarity, geometric_metrics  # noqa: E402

DEFAULT_LEXICON = ROOT / "docs/final/artifacts/logos_scriptures_js_gematria_lexicon_v1.jsonl"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_gematria_matrix_snapshot_v1_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_entries(path: Path, *, max_entries: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen_strongs: set[str] = set()
    with path.open(encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            row = json.loads(s)
            if not isinstance(row, dict):
                continue
            strongs = str(row.get("strongs") or "").strip()
            if not strongs or strongs in seen_strongs:
                continue
            vec = row.get("vector_4d")
            if not isinstance(vec, dict):
                continue
            seen_strongs.add(strongs)
            rows.append(
                {
                    "strongs": strongs,
                    "lemma": row.get("lemma"),
                    "gloss": row.get("gloss"),
                    "gematria": row.get("gematria"),
                    "vector_4d": {k: float(vec[k]) for k in ("S", "L", "K", "M") if k in vec},
                }
            )
            if len(rows) >= max_entries:
                break
    return rows


def build_snapshot(lexicon_path: Path, *, max_entries: int) -> dict[str, Any]:
    entries = _load_entries(lexicon_path, max_entries=max_entries)
    n = len(entries)
    matrix: list[list[float]] = []
    for i in range(n):
        row_vals: list[float] = []
        for j in range(n):
            row_vals.append(round(cosine_similarity(entries[i]["vector_4d"], entries[j]["vector_4d"]), 8))
        matrix.append(row_vals)
    # Hybrid demo: blend first two entries at w=0.35 for metrics block
    hybrid_metrics = None
    if n >= 2:
        from myeongni.gematria_myeongri_math_v1 import blend_convex_renorm

        hybrid = blend_convex_renorm(entries[0]["vector_4d"], entries[1]["vector_4d"], 0.35)
        hybrid_metrics = geometric_metrics(entries[0]["vector_4d"], entries[1]["vector_4d"], hybrid)
    return {
        "schema": "logos_gematria_matrix_snapshot_v1",
        "generated_at_utc": _now(),
        "research_only": True,
        "hypothesis_tier": "B",
        "send_gate": "HOLD",
        "lookup_only": True,
        "prophecy_claims": False,
        "kernel_recipe_id": "gematria_bridge_v1",
        "math_module": "gematria_myeongri_math_v1",
        "source_lexicon": str(lexicon_path.relative_to(ROOT)).replace("\\", "/"),
        "entry_count": n,
        "max_entries_cap": max_entries,
        "entries": entries,
        "cosine_matrix": matrix,
        "hybrid_demo": hybrid_metrics,
        "honesty": {
            "note_ko": "STEPBible lookup + deterministic 4D bridge — not open Q&A gematria OS.",
            "marketing_only_4d_realtime": False,
        },
        "reproduce": f"py scripts/export_logos_gematria_matrix_snapshot_v1.py --max-entries {max_entries}",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lexicon", type=Path, default=DEFAULT_LEXICON)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--max-entries", type=int, default=24)
    args = ap.parse_args()
    if not args.lexicon.is_file():
        print(f"missing lexicon: {args.lexicon}", file=sys.stderr)
        return 1
    doc = build_snapshot(args.lexicon, max_entries=max(2, min(args.max_entries, 64)))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.out} entries={doc['entry_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
