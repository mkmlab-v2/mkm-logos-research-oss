#!/usr/bin/env python3
"""Eval myeongni corpus GraphRAG router vs human chunk-path gold [HYPO][B-track]."""
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

from scripts.build_myeongni_corpus_graphrag_router_v1 import (  # noqa: E402
    DEFAULT_CHUNK_TABLE,
    DEFAULT_MYEONGNI_LENS,
    DEFAULT_STATE_PROBE,
    build_router,
)

DEFAULT_GOLD = ROOT / "docs/final/artifacts/myeongni_corpus_graphrag_gold_human_v1.json"
DEFAULT_OUT = ROOT / "reports/myeongni_corpus_graphrag_gold_eval_v1_latest.json"
DEFAULT_ART = ROOT / "docs/final/artifacts/myeongni_corpus_graphrag_gold_eval_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _path_chunk_ids(paths: list[dict[str, Any]]) -> set[str]:
    out: set[str] = set()
    for p in paths:
        cid = p.get("chunk_id")
        if cid:
            out.add(str(cid))
        for step in p.get("steps") or []:
            s = str(step)
            if s.startswith("chunk::"):
                out.add(s.split("::", 1)[1])
    return out


def _path_sections(paths: list[dict[str, Any]]) -> set[str]:
    out: set[str] = set()
    for p in paths:
        for step in p.get("steps") or []:
            s = str(step)
            if s.startswith("section::"):
                out.add(s.split("::", 1)[1])
    return out


def eval_gold(
    *,
    gold: dict[str, Any],
    chunk_table: Path,
    state_probe: Path,
    myeongni_lens: Path,
    top_k: int,
) -> dict[str, Any]:
    items = gold.get("items") or []
    rows: list[dict[str, Any]] = []
    hits = 0
    for it in items:
        if not isinstance(it, dict):
            continue
        q = str(it.get("query_ko") or "")
        router = build_router(
            query=q,
            chunk_table=chunk_table,
            state_probe=state_probe,
            myeongni_lens=myeongni_lens,
            top_k=top_k,
        )
        paths = router.get("paths") or []
        got_chunks = _path_chunk_ids(paths)
        got_sections = _path_sections(paths)
        gold_chunks = {str(x) for x in (it.get("gold_chunk_ids") or [])}
        gold_sections = {str(x) for x in (it.get("gold_section_keys") or [])}
        chunk_hit = bool(gold_chunks & got_chunks)
        section_hit = bool(gold_sections & got_sections) if gold_sections else False
        row_hit = chunk_hit or section_hit
        if row_hit:
            hits += 1
        rows.append(
            {
                "id": it.get("id"),
                "query_ko": q,
                "chunk_hit": chunk_hit,
                "section_hit": section_hit,
                "hit": row_hit,
                "gold_chunk_ids": sorted(gold_chunks),
                "retrieved_chunk_ids": sorted(got_chunks),
                "gold_section_keys": sorted(gold_sections),
                "retrieved_section_keys": sorted(got_sections),
                "path_count": len(paths),
            }
        )
    n = len(rows)
    rate = round(hits / n, 4) if n else None
    return {
        "schema": "myeongni_corpus_graphrag_gold_eval_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "send_gate": "HOLD",
        "prophecy_vote": "none",
        "gold_pointer": str(DEFAULT_GOLD),
        "n_items": n,
        "path_hit_rate": rate,
        "rows": rows,
        "verdict_ko": (
            f"명리 GraphRAG gold path {hits}/{n} ({rate:.1%}) — 해설·감사 레일만"
            if rate is not None
            else "gold 항목 없음"
        ),
        "reproduce": "py scripts/run_myeongni_corpus_graphrag_gold_eval_v1.py",
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gold-json", type=Path, default=DEFAULT_GOLD)
    ap.add_argument("--chunk-table", type=Path, default=DEFAULT_CHUNK_TABLE)
    ap.add_argument("--state-probe", type=Path, default=DEFAULT_STATE_PROBE)
    ap.add_argument("--myeongni-lens", type=Path, default=DEFAULT_MYEONGNI_LENS)
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument("--min-hit-rate", type=float, default=0.6)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    if not args.gold_json.is_file():
        print(f"Missing gold: {args.gold_json}", file=sys.stderr)
        return 2
    if not args.chunk_table.is_file():
        print(f"Missing chunk table: {args.chunk_table}", file=sys.stderr)
        return 2

    gold = _read(args.gold_json)
    doc = eval_gold(
        gold=gold,
        chunk_table=args.chunk_table,
        state_probe=args.state_probe,
        myeongni_lens=args.myeongni_lens,
        top_k=args.top_k,
    )
    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(payload, encoding="utf-8")
    DEFAULT_ART.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_ART.write_text(payload, encoding="utf-8")

    rate = doc.get("path_hit_rate")
    print(
        json.dumps(
            {
                "ok": True,
                "path_hit_rate": rate,
                "n_items": doc.get("n_items"),
                "out": str(args.output_json),
            },
            ensure_ascii=False,
        )
    )
    if rate is not None and float(rate) < float(args.min_hit_rate):
        print(
            f"WARN: path_hit_rate {rate} < min {args.min_hit_rate} (research gate only)",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
