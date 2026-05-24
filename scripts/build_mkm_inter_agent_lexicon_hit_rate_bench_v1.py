#!/usr/bin/env python3
"""[HYPO] Lexicon hit-rate bench across dialogue corpora (41k atom_id rail)."""

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

DEFAULT_OUT = ROOT / "docs/final/artifacts/mkm_inter_agent_lexicon_hit_rate_bench_v1_latest.json"

CORPORA: dict[str, list[str]] = {
    "trading": [
        "WATCH regime macro fragility BTC REDUCE exposure prophecy dual-leg KOSPI",
        "Prophecy lane B-track divergence HOLD orders risk profile",
    ],
    "health": [
        "환자 건강 수면 식사 증상 호흡 피로 회복 체온 임상 바이탈 Silver Tech",
        "건강검진 회복률 수면 부족 식사 불균형 의료 팀 검토",
    ],
    "lexicon_dense": [
        (
            "strong morph greek logos bible reference message kai mercy alpha beta gamma "
            "delta epsilon zeta eta theta iota kappa lambda mu nu xi omicron pi rho sigma"
        ),
        (
            "hebrew aramaic covenant prophecy wisdom knowledge understanding counsel "
            "might lord god spirit holy righteousness judgment salvation redemption"
        ),
    ],
}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _bench_line(
    text: str,
    path: Path,
) -> dict[str, Any]:
    from scripts.core.master_codebook_lexicon_v1_bridge import (
        lexicon_atom_sequence_for_text,
        lexicon_hits_for_text,
        unicode_word_tokens,
    )

    toks = unicode_word_tokens(text)
    hits, hit_meta = lexicon_hits_for_text(text, path)
    seq, seq_meta = lexicon_atom_sequence_for_text(text, path)
    token_n = len(toks)
    hit_n = len(hits)
    atom_n = len(seq)
    return {
        "char_len": len(text),
        "token_count": token_n,
        "lexicon_hit_count": hit_n,
        "atom_id_count": atom_n,
        "hit_rate_tokens": round(hit_n / token_n, 6) if token_n else None,
        "atom_rate_tokens": round(atom_n / token_n, 6) if token_n else None,
        "hit_meta_status": hit_meta.get("status"),
        "seq_meta_status": seq_meta.get("status"),
    }


def run_bench() -> dict[str, Any]:
    from scripts.core.master_codebook_lexicon_v1_bridge import resolve_latest_codebook_path

    path = resolve_latest_codebook_path()
    if path is None:
        return {"ok": False, "error": "lexicon_path_missing"}

    corpora_out: dict[str, Any] = {}
    for name, lines in CORPORA.items():
        rows = [_bench_line(line, path) for line in lines]
        hit_rates = [r["hit_rate_tokens"] for r in rows if r.get("hit_rate_tokens") is not None]
        atom_rates = [r["atom_rate_tokens"] for r in rows if r.get("atom_rate_tokens") is not None]
        corpora_out[name] = {
            "lines": rows,
            "avg_hit_rate_tokens": round(sum(hit_rates) / len(hit_rates), 6) if hit_rates else None,
            "avg_atom_rate_tokens": round(sum(atom_rates) / len(atom_rates), 6) if atom_rates else None,
        }

    dense = corpora_out.get("lexicon_dense", {})
    trading = corpora_out.get("trading", {})
    return {
        "ok": True,
        "schema": "mkm_inter_agent_lexicon_hit_rate_bench_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "lexicon_path": str(path.resolve()),
        "corpora": corpora_out,
        "summary": {
            "lexicon_dense_avg_atom_rate": dense.get("avg_atom_rate_tokens"),
            "trading_avg_atom_rate": trading.get("avg_atom_rate_tokens"),
            "dense_over_trading_atom_rate_ratio": (
                round(
                    float(dense["avg_atom_rate_tokens"]) / float(trading["avg_atom_rate_tokens"]),
                    4,
                )
                if dense.get("avg_atom_rate_tokens") and trading.get("avg_atom_rate_tokens")
                else None
            ),
        },
        "boundary_ack": "Token-level hit rate only; not Track A bench or live trading.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    doc = run_bench()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    return 0 if doc.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
