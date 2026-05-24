#!/usr/bin/env python3
"""[HYPO] Rewrite chunk-lane compressed_text via atom substitution (optional lane copy)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ijeoma_cjk_compression_hypo_v1 import (  # noqa: E402
    compress_ijeoma_cjk_substitution,
    expand_ijeoma_cjk_substitution,
    resolve_marker_strategy,
    resolve_shorter_by,
)

DEFAULT_IN = ROOT / "docs/final/artifacts/universal_compression_bench_lane_ijeoma_chunk_table_v1.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/universal_compression_bench_lane_ijeoma_chunk_cjk_hypo_v1.json"
OUT_O200K_TIGHT = ROOT / "docs/final/artifacts/universal_compression_bench_lane_ijeoma_chunk_cjk_o200k_tight_v1.json"
HYPO_LEX = ROOT / "reports/constitution/btrack_pilot/ijeoma_hanja_codebook_lexicon_v1_hypo_latest.json"

LANE_ID_BY_MARKER: dict[str, str] = {
    "pua": "ijeoma_chunk_table_cjk_hypo_v1",
    "ascii_compact": "ijeoma_chunk_table_cjk_ascii_compact_v1",
    "o200k_tight": "ijeoma_chunk_table_cjk_o200k_tight_v1",
    "atom_id": "ijeoma_chunk_table_cjk_atom_id_v1",
}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in-lane", type=Path, default=DEFAULT_IN)
    ap.add_argument("--out-lane", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--lexicon-json", type=Path, default=HYPO_LEX)
    ap.add_argument(
        "--marker-strategy",
        choices=("pua", "ascii_compact", "atom_id", "o200k_tight"),
        default=None,
        help="Default: resolve_marker_strategy() (env MKM_IJEOMA_CJK_MARKER_STRATEGY or ascii_compact).",
    )
    ap.add_argument(
        "--shorter-by",
        choices=("tokens", "chars", "o200k"),
        default=None,
        help="Default: resolve_shorter_by() (env MKM_IJEOMA_CJK_SHORTER_BY or tokens).",
    )
    ap.add_argument(
        "--no-only-if-shorter",
        action="store_true",
        help="Replace even when marker token count >= phrase (max coverage).",
    )
    args = ap.parse_args()

    marker_strategy = resolve_marker_strategy(args.marker_strategy)
    shorter_by = resolve_shorter_by(args.shorter_by)

    in_path = (ROOT / args.in_lane).resolve() if not args.in_lane.is_absolute() else args.in_lane
    out_path = (ROOT / args.out_lane).resolve() if not args.out_lane.is_absolute() else args.out_lane
    lex_path = (ROOT / args.lexicon_json).resolve() if not args.lexicon_json.is_absolute() else args.lexicon_json

    doc = json.loads(in_path.read_text(encoding="utf-8"))
    total_repl = 0
    for case in doc.get("compression_cases") or []:
        raw = str(case.get("raw_text") or "")
        comp, meta = compress_ijeoma_cjk_substitution(
            raw,
            lex_path,
            only_if_shorter=not args.no_only_if_shorter,
            marker_strategy=marker_strategy,
            shorter_by=shorter_by,
        )
        rec = expand_ijeoma_cjk_substitution(comp, lex_path, marker_strategy=marker_strategy)
        case["compressed_text"] = comp
        case["reconstructed_text"] = rec
        case["ijeoma_cjk_substitution_hypo_v1"] = True
        case["ijeoma_cjk_marker_strategy"] = marker_strategy
        case["ijeoma_cjk_shorter_by"] = shorter_by
        total_repl += int(meta.get("replacements") or 0)

    doc["lane_id"] = LANE_ID_BY_MARKER.get(
        marker_strategy, f"ijeoma_chunk_table_cjk_{marker_strategy}_v1"
    )
    doc["marker_strategy"] = marker_strategy
    doc["shorter_by"] = shorter_by
    doc["generated_at_utc"] = _utc()
    doc["research_only"] = True
    doc["hypothesis_tier"] = "B"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "wrote": str(out_path.relative_to(ROOT)).replace("\\", "/"),
                "case_count": len(doc.get("compression_cases") or []),
                "total_replacements": total_repl,
                "marker_strategy": marker_strategy,
                "shorter_by": shorter_by,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
