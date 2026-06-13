#!/usr/bin/env python3
"""LTM graph route accuracy bench — graph routing vs blind token overlap ([HYPO]).

  py scripts/bench_mkm_ltm_route_accuracy_v1.py
  py scripts/bench_mkm_ltm_route_accuracy_v1.py --out reports/mkm_ltm_route_accuracy_bench_v1_latest.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_ROOT / "scripts"))

from mkm_long_term_memory_graph_lib_v1 import (  # noqa: E402
    DEFAULT_GRAPH_PATH,
    load_graph,
    resolve_lane_from_graph,
    route_concepts_by_query,
    utc_now_iso,
)

DEFAULT_CORPUS = (
    SCRIPT_ROOT / "docs" / "final" / "artifacts" / "mkm_ltm_route_accuracy_corpus_v1.json"
)


def _tokenize(query: str) -> list[str]:
    return [t for t in re.split(r"[^a-zA-Z0-9_가-힣$]+", query.lower()) if len(t) >= 2]


def blind_top1_concept(graph: dict[str, Any], query: str) -> str | None:
    """Naive baseline: token overlap in essence+aliases only (no field_tags, no alias boost)."""
    tokens = _tokenize(query)
    if not tokens:
        return None
    best_id: str | None = None
    best_score = 0
    for concept_id, concept in (graph.get("concepts") or {}).items():
        hay = " ".join(
            [
                str(concept.get("essence") or ""),
                str(concept.get("label_ko") or ""),
                " ".join(str(a) for a in concept.get("query_aliases") or []),
            ]
        ).lower()
        score = sum(1 for t in tokens if t in hay)
        if score > best_score or (score == best_score and score > 0 and (best_id is None or concept_id < best_id)):
            best_score = score
            best_id = concept_id
    return best_id if best_score > 0 else None


def load_corpus(path: Path) -> list[dict[str, Any]]:
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    if doc.get("schema") != "mkm_ltm_route_accuracy_corpus_v1":
        raise ValueError(f"unexpected corpus schema: {doc.get('schema')!r}")
    return list(doc.get("cases") or [])


def evaluate_case(graph: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    query = str(case.get("query") or "")
    expect_any = list(case.get("expect_top1_any") or [])
    expect_lane = case.get("expect_lane")

    routed = route_concepts_by_query(
        graph, query, min_score=2, max_concepts=5, include_related=False
    )
    graph_top1 = routed[0][0] if routed else None
    blind_top1 = blind_top1_concept(graph, query)
    resolved_lane = resolve_lane_from_graph(graph, query)

    graph_hit = graph_top1 in expect_any if expect_any else graph_top1 is not None
    blind_hit = blind_top1 in expect_any if expect_any else blind_top1 is not None
    graph_only_hit = graph_hit and not blind_hit
    lane_hit = True
    if expect_lane is not None:
        lane_hit = resolved_lane == expect_lane

    return {
        "id": case.get("id"),
        "query": query,
        "expect_top1_any": expect_any,
        "expect_lane": expect_lane,
        "graph_top1": graph_top1,
        "blind_top1": blind_top1,
        "resolved_lane": resolved_lane,
        "graph_top1_hit": graph_hit,
        "blind_top1_hit": blind_hit,
        "graph_only_hit": graph_only_hit,
        "lane_hit": lane_hit,
        "routed_top5": [cid for cid, _ in routed[:5]],
    }


def graph_only_cause_line(result: dict[str, Any], graph: dict[str, Any]) -> str:
    """One-line explanation why graph routing beat blind baseline."""
    blind_id = result.get("blind_top1")
    graph_id = result.get("graph_top1")
    query = str(result.get("query") or "").lower()
    concepts = graph.get("concepts") or {}
    blind_c = concepts.get(blind_id) or {} if blind_id else {}
    graph_c = concepts.get(graph_id) or {} if graph_id else {}

    graph_tag_hits = [
        str(t)
        for t in graph_c.get("field_tags") or []
        if len(str(t)) >= 3 and str(t).lower() in query
    ]
    blind_tag_hits = [
        str(t)
        for t in blind_c.get("field_tags") or []
        if len(str(t)) >= 3 and str(t).lower() in query
    ]
    tag_delta = [t for t in graph_tag_hits if t not in blind_tag_hits]
    if tag_delta:
        tags = ", ".join(tag_delta[:3])
        return (
            f"graph field_tags ({tags}) + priority disambiguate; "
            "blind uses essence/alias overlap only"
        )

    graph_pri = int(graph_c.get("priority") or 0)
    blind_pri = int(blind_c.get("priority") or 0)
    if graph_pri > blind_pri:
        return (
            f"blind picks {blind_id!r} on token overlap; graph priority "
            f"({graph_pri}>{blind_pri}) routes {graph_id!r}"
        )

    if blind_id and graph_id and blind_id < graph_id:
        return (
            f"blind token tie → alphabetical id {blind_id!r}; "
            f"graph uses field_tags + priority → {graph_id!r}"
        )

    return (
        f"blind picks {blind_id!r} on shared tokens; graph scorer "
        f"(field_tags/alias boost/priority) → {graph_id!r}"
    )


def build_graph_only_cases(
    results: list[dict[str, Any]], graph: dict[str, Any]
) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for result in results:
        if not result.get("graph_only_hit"):
            continue
        cases.append(
            {
                "id": result["id"],
                "query": result["query"],
                "blind_top1": result["blind_top1"],
                "graph_top1": result["graph_top1"],
                "expect_top1_any": result["expect_top1_any"],
                "cause": graph_only_cause_line(result, graph),
            }
        )
    return cases


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspace-root", type=Path, default=SCRIPT_ROOT)
    ap.add_argument("--graph", type=Path, default=DEFAULT_GRAPH_PATH)
    ap.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    ap.add_argument(
        "--out",
        type=Path,
        default=SCRIPT_ROOT / "reports" / "mkm_ltm_route_accuracy_bench_v1_latest.json",
    )
    ap.add_argument(
        "--min-graph-top1-rate",
        type=float,
        default=0.75,
        help="Exit 1 if graph top-1 hit rate below this (default 0.75).",
    )
    ap.add_argument(
        "--min-lane-hit-rate",
        type=float,
        default=0.85,
        help="Exit 1 if lane hit rate below this when lane cases exist (default 0.85).",
    )
    ap.add_argument(
        "--min-graph-only-hits",
        type=int,
        default=1,
        help="Exit 1 if graph-only hits (graph hit, blind miss) below this (default 1).",
    )
    args = ap.parse_args()

    if not args.graph.is_file():
        print(f"FAIL: graph missing: {args.graph}", file=sys.stderr)
        return 1
    if not args.corpus.is_file():
        print(f"FAIL: corpus missing: {args.corpus}", file=sys.stderr)
        return 1

    graph = load_graph(args.graph)
    cases = load_corpus(args.corpus)
    if not cases:
        print("FAIL: empty corpus", file=sys.stderr)
        return 1

    results = [evaluate_case(graph, case) for case in cases]
    n = len(results)
    graph_hits = sum(1 for r in results if r["graph_top1_hit"])
    blind_hits = sum(1 for r in results if r["blind_top1_hit"])
    lane_cases = [r for r in results if r["expect_lane"] is not None]
    lane_hits = sum(1 for r in lane_cases if r["lane_hit"])
    graph_only_hits = sum(1 for r in results if r["graph_only_hit"])

    graph_rate = round(graph_hits / n, 4)
    blind_rate = round(blind_hits / n, 4)
    lane_rate = round(lane_hits / len(lane_cases), 4) if lane_cases else None
    delta = round(graph_rate - blind_rate, 4)

    doc: dict[str, Any] = {
        "schema": "mkm_ltm_route_accuracy_bench_v1",
        "track": "B",
        "research_only": True,
        "hypothesis_tier": "B",
        "boundary_ack": "[HYPO] route accuracy bench — not Track A promotion proof",
        "generated_at_utc": utc_now_iso(),
        "graph_path": str(args.graph.relative_to(args.workspace_root)).replace("\\", "/"),
        "corpus_path": str(args.corpus.relative_to(args.workspace_root)).replace("\\", "/"),
        "case_count": n,
        "aggregate": {
            "graph_top1_hit_rate": graph_rate,
            "blind_top1_hit_rate": blind_rate,
            "delta_graph_minus_blind": delta,
            "graph_only_hit_count": graph_only_hits,
            "lane_hit_rate": lane_rate,
            "lane_case_count": len(lane_cases),
        },
        "graph_only_cases": build_graph_only_cases(results, graph),
        "cases": results,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"WROTE: {args.out}")
    print(
        f"graph_top1_hit_rate={graph_rate} blind_top1_hit_rate={blind_rate} "
        f"delta={delta} graph_only_hits={graph_only_hits} lane_hit_rate={lane_rate}"
    )

    if graph_rate < args.min_graph_top1_rate:
        misses = [r["id"] for r in results if not r["graph_top1_hit"]]
        print(
            f"FAIL: graph_top1_hit_rate {graph_rate} < {args.min_graph_top1_rate}; "
            f"misses={misses}",
            file=sys.stderr,
        )
        return 1
    if lane_rate is not None and lane_rate < args.min_lane_hit_rate:
        misses = [r["id"] for r in lane_cases if not r["lane_hit"]]
        print(
            f"FAIL: lane_hit_rate {lane_rate} < {args.min_lane_hit_rate}; "
            f"misses={misses}",
            file=sys.stderr,
        )
        return 1
    if graph_only_hits < args.min_graph_only_hits:
        print(
            f"FAIL: graph_only_hit_count {graph_only_hits} < {args.min_graph_only_hits}; "
            "graph routing must beat blind baseline on at least one case",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
