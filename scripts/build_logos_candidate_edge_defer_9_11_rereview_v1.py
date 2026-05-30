#!/usr/bin/env python3
"""Wave 3 re-review for defer ranks 9·11 — cross-ref A-D dissection; default defer_maintained."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DISSECTION = ROOT / "reports/logos_candidate_edge_defer_9_11_dissection_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/logos_candidate_edge_defer_9_11_rereview_v1_latest.json"
SCHEMA = "logos_candidate_edge_defer_9_11_rereview_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    obj = json.loads(path.read_text(encoding="utf-8-sig"))
    return obj if isinstance(obj, dict) else {}


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _books_from_pair(pair_key: str) -> list[str]:
    books: list[str] = []
    for part in str(pair_key).split("|"):
        if "::" in part:
            ref = part.split("::", 1)[1]
            if "." in ref:
                books.append(ref.split(".", 1)[0])
    return books


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dissection-json", type=Path, default=DEFAULT_DISSECTION)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--decision",
        default="defer_maintained",
        choices=("defer_maintained", "approve", "reject"),
        help="Wave 3 commander outcome (default: defer_maintained)",
    )
    ap.add_argument("--reviewer", default="commander_wave3_parallel")
    args = ap.parse_args()

    dis_path = args.dissection_json if args.dissection_json.is_absolute() else ROOT / args.dissection_json
    dis = _read_json(dis_path)
    pairs = {p.get("queue_rank"): p for p in dis.get("pairs_analyzed") or [] if isinstance(p, dict)}
    if not pairs.get(9) or not pairs.get(11):
        print(json.dumps({"ok": False, "error": f"missing rank 9/11 in dissection: {dis_path}"}))
        return 1

    items: list[dict[str, Any]] = []
    for rank in (9, 11):
        p = pairs[rank]
        d_dec = (p.get("D_decision") or {}) if isinstance(p.get("D_decision"), dict) else {}
        rec = str(d_dec.get("recommendation") or "defer_maintain")
        items.append(
            {
                "queue_rank": rank,
                "pair_key": p.get("pair_key"),
                "similarity": p.get("similarity") or p.get("ann_lite_similarity"),
                "cross_book": p.get("cross_book"),
                "books": p.get("books") or _books_from_pair(str(p.get("pair_key") or "")),
                "dissection_recommendation": rec,
                "embedding_pattern_ko": (p.get("B_embedding_neighbors") or {}).get("pattern_note_ko"),
                "rationale_ko": d_dec.get("rationale_ko")
                or (p.get("C_human_theme_reading_ko") or [None])[0],
                "recommendation": "defer" if args.decision == "defer_maintained" else args.decision,
            }
        )

    doc = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tier": "B",
        "wave": 3,
        "decision": args.decision,
        "reviewer": args.reviewer,
        "dissection_ref": _rel(dis_path),
        "merge_to_canonical_allowed": False,
        "reject_blocked_policy_ko": "rank 9·11 reject 금지 — dissection 이력 보존(defer_maintain)",
        "items": items,
        "baseline_neighbors": {
            "rank_8": pairs.get(8, {}).get("pair_key"),
            "rank_10": pairs.get(10, {}).get("pair_key"),
            "note_ko": "intra-Gen baseline approve; cross-book Gen↔Jer defer 유지",
        },
    }

    out = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out), "decision": args.decision, "wave": 3}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
