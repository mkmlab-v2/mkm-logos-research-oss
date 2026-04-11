#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.75, L:0.55, K:0.85, M:0.25}
# Balance: 87
# Purpose: Propose per-shard codebook soft-term candidates from Jaccard loss patterns with heuristics.
# Keywords: codebook, shard, compression, jaccard, patch
"""Build shard-scoped injection proposals from loss patterns (no direct shard mutation)."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_LOSS = ROOT / "reports" / "constitution" / "btrack_pilot" / "compression_jaccard_loss_patterns_latest.json"
DEFAULT_AGG = ROOT / "reports" / "constitution" / "btrack_pilot" / "compression_jaccard_loss_patterns_aggregated_v1.json"
DEFAULT_OUT = ROOT / "reports" / "constitution" / "btrack_pilot" / "shard_patch_proposal_v1.json"

# 서술·접속·대명 등: 정보 밀도가 낮고 Jaccard만 올리기 쉬운 형태를 걸러낸다(확장 가능).
_FUNCTIONAL_STOPWORDS: frozenset[str] = frozenset(
    {
        # Korean (common endings / auxiliaries / pronouns)
        "한다",
        "된다",
        "있다",
        "없다",
        "이다",
        "하다",
        "되다",
        "같다",
        "위해",
        "통해",
        "대해",
        "같이",
        "함께",
        "같은",
        "그리고",
        "하지만",
        "그러나",
        "때문",
        "경우",
        "때문에",
        "있어",
        "없어",
        "해야",
        "되어",
        "하는",
        "되는",
        "있는",
        "없는",
        "같은",
        "이런",
        "저런",
        "그런",
        "어떤",
        "무엇",
        "어떻게",
        "그것",
        "것",
        # English glue (loss report is mixed)
        "the",
        "a",
        "an",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "to",
        "of",
        "in",
        "on",
        "for",
        "and",
        "or",
        "but",
        "not",
        "as",
        "at",
        "by",
        "it",
        "its",
        "this",
        "that",
        "these",
        "those",
    }
)


def _is_numeric_token(t: str) -> bool:
    s = t.strip()
    if not s:
        return True
    if s.isdigit():
        return True
    # e.g. 3.14, 1e2
    if re.fullmatch(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", s):
        return True
    return False


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Shard patch proposal from Jaccard loss patterns.")
    p.add_argument("--loss-patterns", type=Path, default=DEFAULT_LOSS, help="compression_jaccard_loss_patterns_*.json")
    p.add_argument("--aggregated", type=Path, default=DEFAULT_AGG, help="aggregated_v1 (checksum / summary only)")
    p.add_argument("--output", type=Path, default=DEFAULT_OUT)
    p.add_argument("--min-global-count", type=int, default=2)
    p.add_argument("--min-shard-concentration", type=float, default=0.5, help="Flag tokens with max_shard_share >= this")
    p.add_argument(
        "--mode",
        choices=("strict", "permissive"),
        default="permissive",
        help="strict: only tokens meeting concentration floor; permissive: all heuristic-pass tokens assigned to argmax shard",
    )
    return p


def main() -> int:
    args = _parser().parse_args()
    loss_doc = json.loads(args.loss_patterns.read_text(encoding="utf-8"))
    cases = loss_doc.get("cases") or []

    global_c: Counter[str] = Counter()
    by_shard: dict[str, Counter[str]] = defaultdict(Counter)

    for row in cases:
        sid = str(row.get("shard_id") or "unknown")
        lost = row.get("words_lost_sample") or []
        if not isinstance(lost, list):
            continue
        for t in lost:
            if not isinstance(t, str):
                continue
            w = t.strip()
            if not w:
                continue
            global_c[w] += 1
            by_shard[sid][w] += 1

    min_freq = max(1, int(args.min_global_count))
    conc_floor = float(args.min_shard_concentration)
    mode = str(args.mode)

    excluded: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []

    for token, total in global_c.items():
        if total < min_freq:
            excluded.append({"token": token, "reason": "below_min_global_count", "count": total})
            continue
        if len(token) <= 1:
            excluded.append({"token": token, "reason": "single_grapheme", "count": total})
            continue
        if _is_numeric_token(token):
            excluded.append({"token": token, "reason": "numeric", "count": total})
            continue
        tl = token.lower()
        if tl in _FUNCTIONAL_STOPWORDS or token in _FUNCTIONAL_STOPWORDS:
            excluded.append({"token": token, "reason": "functional_stopword", "count": total})
            continue

        shard_parts = [(s, by_shard[s][token]) for s in by_shard if by_shard[s][token] > 0]
        if not shard_parts:
            continue
        # Higher count wins; on tie, lexicographically smallest shard_id (reproducible).
        primary_shard, max_c = min(shard_parts, key=lambda x: (-x[1], x[0]))
        conc = max_c / float(total) if total else 0.0
        concentrated = conc >= conc_floor

        if mode == "strict" and not concentrated:
            excluded.append({"token": token, "reason": "below_concentration_floor", "count": total, "concentration": conc})
            continue

        candidates.append(
            {
                "token": token,
                "global_count": int(total),
                "primary_shard_id": primary_shard,
                "max_shard_count": int(max_c),
                "shard_concentration": round(conc, 6),
                "concentrated": concentrated,
                "per_shard_counts": {s: int(by_shard[s][token]) for s in sorted(by_shard) if by_shard[s][token] > 0},
            }
        )

    by_shard_queue: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for c in candidates:
        by_shard_queue[str(c["primary_shard_id"])].append(c)

    for sid in by_shard_queue:
        by_shard_queue[sid].sort(key=lambda x: (-x["global_count"], x["token"]))

    agg_checksum: dict[str, Any] | None = None
    if args.aggregated.is_file():
        agg = json.loads(args.aggregated.read_text(encoding="utf-8"))
        agg_checksum = {
            "case_count": (agg.get("summary") or {}).get("case_count"),
            "unique_tokens_lost": (agg.get("summary") or {}).get("unique_tokens_lost"),
            "total_token_occurrences": (agg.get("summary") or {}).get("total_token_occurrences"),
        }

    out: dict[str, Any] = {
        "schema": "shard_patch_proposal_v1",
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "sources": {
            "loss_patterns": str(args.loss_patterns.resolve()),
            "aggregated_optional": str(args.aggregated.resolve()) if args.aggregated.is_file() else None,
        },
        "parameters": {
            "min_global_count": min_freq,
            "min_shard_concentration_for_flag": conc_floor,
            "mode": mode,
            "functional_stopword_count": len(_FUNCTIONAL_STOPWORDS),
        },
        "aggregated_summary_checksum": agg_checksum,
        "notes": [
            "Does not modify codebook files; human review before merge.",
            "Virtual Jaccard delta is not simulated here; re-run bench after manual shard edits.",
        ],
        "summary": {
            "case_count_in_loss_doc": len(cases),
            "candidate_token_count": len(candidates),
            "excluded_record_count": len(excluded),
            "shard_ids_with_candidates": sorted(by_shard_queue.keys()),
        },
        "by_shard_id": {k: v for k, v in sorted(by_shard_queue.items())},
        "candidates_flat": sorted(candidates, key=lambda x: (-x["global_count"], x["token"])),
        "excluded": excluded[:500],
        "excluded_truncated": len(excluded) > 500,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()} candidates={len(candidates)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
