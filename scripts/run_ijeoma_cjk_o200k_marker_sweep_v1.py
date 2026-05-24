#!/usr/bin/env python3
"""[HYPO] Sweep CJK markers + shorter_by gates for o200k_base corpus savings (B-track)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ijeoma_cjk_compression_hypo_v1 import (  # noqa: E402
    _load_lexicon_maps,
    compress_ijeoma_cjk_substitution,
    default_hypo_lexicon_path,
)
from scripts.report_multilens_performance_eval import _o200k_saving_rate, _tiktoken_o200k_status  # noqa: E402

LANE = ROOT / "docs/final/artifacts/universal_compression_bench_lane_ijeoma_chunk_table_v1.json"
OUT = ROOT / "reports/constitution/btrack_pilot/comp_ijeoma_cjk_o200k_marker_sweep_v1.json"

VARIANTS: list[tuple[str, str, bool]] = [
    ("ascii_compact", "tokens", True),
    ("ascii_compact", "o200k", True),
    ("o200k_tight", "tokens", True),
    ("o200k_tight", "o200k", True),
    ("o200k_tight", "o200k", False),
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _bench_variant(
    cases: list[dict[str, Any]],
    lex_path: Path,
    marker_strategy: str,
    shorter_by: str,
    only_if_shorter: bool,
    enc: Any,
) -> dict[str, Any]:
    _load_lexicon_maps.cache_clear()
    proxy_rates: list[float] = []
    o2_raw = o2_comp = 0
    negative = 0
    repl_total = 0
    skipped = 0
    for case in cases:
        raw = str(case.get("raw_text") or "")
        comp, meta = compress_ijeoma_cjk_substitution(
            raw,
            lex_path,
            marker_strategy=marker_strategy,
            shorter_by=shorter_by,
            only_if_shorter=only_if_shorter,
        )
        proxy_rates.append(float(meta.get("token_saving_rate_proxy") or 0.0))
        repl_total += int(meta.get("replacements") or 0)
        skipped += int(meta.get("skipped_longer_marker") or 0)
        if enc is not None:
            r = len(enc.encode(raw))
            c = len(enc.encode(comp))
            o2_raw += r
            o2_comp += c
            if _o200k_saving_rate(r, c) < 0:
                negative += 1
    key = f"{marker_strategy}|{shorter_by}|only_if_shorter={only_if_shorter}"
    return {
        "variant_key": key,
        "marker_strategy": marker_strategy,
        "shorter_by": shorter_by,
        "only_if_shorter": only_if_shorter,
        "mean_token_saving_rate_proxy": sum(proxy_rates) / len(proxy_rates) if proxy_rates else 0.0,
        "corpus_o200k_token_saving_rate": _o200k_saving_rate(o2_raw, o2_comp) if o2_raw else None,
        "negative_o200k_per_case_count": negative if enc is not None else None,
        "total_replacements": repl_total,
        "total_skipped_longer": skipped,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lane-json", type=Path, default=LANE)
    ap.add_argument("--lexicon-json", type=Path, default=None)
    ap.add_argument("--max-cases", type=int, default=0)
    ap.add_argument("--out-json", type=Path, default=OUT)
    args = ap.parse_args()

    enc, err = _tiktoken_o200k_status()
    if enc is None:
        print(json.dumps({"error": "tiktoken_unavailable", "reason": err}, ensure_ascii=False))
        return 2

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

    profiles = [_bench_variant(cases, lex_path, ms, sb, oif, enc) for ms, sb, oif in VARIANTS]
    with_o2 = [p for p in profiles if p.get("corpus_o200k_token_saving_rate") is not None]
    best_o2 = max(with_o2, key=lambda p: float(p["corpus_o200k_token_saving_rate"] or -999)) if with_o2 else None
    positive_o2 = [p for p in with_o2 if float(p["corpus_o200k_token_saving_rate"] or 0) > 0]

    out = {
        "schema": "comp_ijeoma_cjk_o200k_marker_sweep_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "case_count": len(cases),
        "lexicon_json": str(lex_path.relative_to(ROOT)).replace("\\", "/"),
        "profiles": {p["variant_key"]: p for p in profiles},
        "recommendation": {
            "best_corpus_o200k": best_o2["variant_key"] if best_o2 else None,
            "corpus_o200k_positive_variants": [p["variant_key"] for p in positive_o2],
            "proxy_headline_stays": "ascii_compact|tokens (operational hook; billing may differ)",
            "note": "B-track only; corpus o200k>0 does not auto-promote Track A / MS 47.5%.",
        },
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "wrote": out_path.name,
                "recommendation": out["recommendation"],
                "best_o200k_rate": best_o2.get("corpus_o200k_token_saving_rate") if best_o2 else None,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
