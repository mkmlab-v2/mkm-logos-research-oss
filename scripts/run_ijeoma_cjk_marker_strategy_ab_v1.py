#!/usr/bin/env python3
"""[HYPO] Compare CJK marker strategies: PUA vs ascii_compact vs atom_id (proxy + o200k)."""

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
OUT = ROOT / "reports/constitution/btrack_pilot/comp_ijeoma_cjk_marker_strategy_ab_v1.json"

STRATEGIES = ("pua", "ascii_compact", "o200k_tight", "atom_id")


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _bench_strategy(
    cases: list[dict[str, Any]],
    lex_path: Path,
    strategy: str,
    enc: Any,
) -> dict[str, Any]:
    _load_lexicon_maps.cache_clear()
    proxy_rates: list[float] = []
    o2_raw = o2_comp = 0
    negative = 0
    repl_total = 0
    for case in cases:
        raw = str(case.get("raw_text") or "")
        comp, meta = compress_ijeoma_cjk_substitution(
            raw, lex_path, marker_strategy=strategy
        )
        proxy_rates.append(float(meta.get("token_saving_rate_proxy") or 0.0))
        repl_total += int(meta.get("replacements") or 0)
        if enc is not None:
            r = len(enc.encode(raw))
            c = len(enc.encode(comp))
            o2_raw += r
            o2_comp += c
            if _o200k_saving_rate(r, c) < 0:
                negative += 1
    return {
        "marker_strategy": strategy,
        "mean_token_saving_rate_proxy": sum(proxy_rates) / len(proxy_rates) if proxy_rates else 0.0,
        "corpus_o200k_token_saving_rate": _o200k_saving_rate(o2_raw, o2_comp) if o2_raw else None,
        "o200k_tokens_raw_total": o2_raw or None,
        "o200k_tokens_compressed_total": o2_comp or None,
        "negative_o200k_per_case_count": negative if enc is not None else None,
        "total_replacements": repl_total,
        "sample_marker_len_mean": _sample_marker_len_mean(lex_path, strategy),
    }


def _sample_marker_len_mean(lex_path: Path, strategy: str) -> float:
    form_to_marker, _ = _load_lexicon_maps(str(lex_path.resolve()), strategy)
    if not form_to_marker:
        return 0.0
    lens = [len(m) for m in form_to_marker.values()]
    return sum(lens) / len(lens)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lane-json", type=Path, default=LANE)
    ap.add_argument("--lexicon-json", type=Path, default=None)
    ap.add_argument("--max-cases", type=int, default=0)
    ap.add_argument("--out-json", type=Path, default=OUT)
    args = ap.parse_args()

    enc, err = _tiktoken_o200k_status()
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

    profiles = [_bench_strategy(cases, lex_path, s, enc) for s in STRATEGIES]
    best_proxy = max(profiles, key=lambda p: p["mean_token_saving_rate_proxy"])
    best_o2 = None
    with_o2 = [p for p in profiles if p.get("corpus_o200k_token_saving_rate") is not None]
    if with_o2:
        best_o2 = max(with_o2, key=lambda p: float(p["corpus_o200k_token_saving_rate"] or -999))

    out = {
        "schema": "comp_ijeoma_cjk_marker_strategy_ab_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "case_count": len(cases),
        "lexicon_json": str(lex_path.relative_to(ROOT)).replace("\\", "/"),
        "tiktoken_o200k_available": enc is not None,
        "tiktoken_error": err,
        "profiles": {p["marker_strategy"]: p for p in profiles},
        "recommendation": {
            "proxy_headline": best_proxy["marker_strategy"],
            "o200k_billing_if_any": best_o2["marker_strategy"] if best_o2 else None,
            "note": "B-track only; do not promote to Track A / MS 47.5% without human + billing review.",
        },
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "wrote": out_path.name,
                "recommendation": out["recommendation"],
                "profiles": {k: {
                    "proxy": v["mean_token_saving_rate_proxy"],
                    "corpus_o200k": v.get("corpus_o200k_token_saving_rate"),
                } for k, v in out["profiles"].items()},
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
