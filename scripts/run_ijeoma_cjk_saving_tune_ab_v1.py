#!/usr/bin/env python3
"""[HYPO] Compare CJK compress only_if_shorter modes on chunk lane (B-track)."""

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
    _load_lexicon_maps,
    compress_ijeoma_cjk_substitution,
    default_hypo_lexicon_path,
)

LANE = ROOT / "docs/final/artifacts/universal_compression_bench_lane_ijeoma_chunk_table_v1.json"
OUT = ROOT / "reports/constitution/btrack_pilot/comp_ijeoma_cjk_saving_tune_ab_v1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lane-json", type=Path, default=LANE)
    ap.add_argument("--lexicon-json", type=Path, default=None)
    ap.add_argument("--out-json", type=Path, default=OUT)
    ap.add_argument("--max-cases", type=int, default=0)
    args = ap.parse_args()

    _load_lexicon_maps.cache_clear()
    lane_path = (ROOT / args.lane_json).resolve() if not args.lane_json.is_absolute() else args.lane_json
    lex_path = (
        Path(args.lexicon_json).resolve()
        if args.lexicon_json
        else default_hypo_lexicon_path()
    )
    out_path = (ROOT / args.out_json).resolve() if not args.out_json.is_absolute() else args.out_json

    cases = json.loads(lane_path.read_text(encoding="utf-8")).get("compression_cases") or []
    if args.max_cases > 0:
        cases = cases[: args.max_cases]

    profiles = [
        ("chars_strict", True, "chars"),
        ("tokens_default", True, "tokens"),
        ("off", False, "tokens"),
    ]
    agg: dict[str, dict[str, float]] = {}
    for name, only_short, shorter_by in profiles:
        savings: list[float] = []
        repl_total = 0
        skip_total = 0
        for case in cases:
            raw = str(case.get("raw_text") or "")
            _, meta = compress_ijeoma_cjk_substitution(
                raw,
                lex_path,
                only_if_shorter=only_short,
                shorter_by=shorter_by,
            )
            savings.append(float(meta.get("token_saving_rate_proxy") or 0.0))
            repl_total += int(meta.get("replacements") or 0)
            skip_total += int(meta.get("skipped_longer_marker") or 0)
        agg[name] = {
            "mean_token_saving_rate_proxy": sum(savings) / len(savings) if savings else 0.0,
            "total_replacements": repl_total,
            "total_skipped_longer": skip_total,
        }

    out = {
        "schema": "comp_ijeoma_cjk_saving_tune_ab_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "case_count": len(cases),
        "lexicon_json": str(lex_path.relative_to(ROOT)).replace("\\", "/"),
        "profiles": agg,
        "recommendation": "tokens_default for eval alignment; off if max coverage needed",
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": out_path.name, "profiles": agg}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
