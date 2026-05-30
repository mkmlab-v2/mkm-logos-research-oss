#!/usr/bin/env python3
"""Aggregate magic orb insight baseline metrics (engine-only, no UI)."""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "magic_orb_insight_baseline_v0_latest.json"
FIXTURE = ROOT / "docs/final/fixtures/magic_orb_question_insight_queries_v1.json"
LIVE_PROBE_UA = "MKM-magic-orb-baseline-v0/1.0"

_DEFAULT_EXPAND = frozenset({"q01", "q03", "q04", "q05"})


def _load_rows() -> list[tuple[str, str, bool]]:
    if FIXTURE.is_file():
        doc = json.loads(FIXTURE.read_text(encoding="utf-8-sig"))
        rows: list[tuple[str, str, bool]] = []
        for it in doc.get("items") or []:
            if not isinstance(it, dict) or not it.get("id") or not it.get("query_ko"):
                continue
            qid = str(it["id"])
            expand = bool(it.get("expand_graph", qid in _DEFAULT_EXPAND))
            rows.append((qid, str(it["query_ko"]), expand))
        if rows:
            return rows
    return [
        ("q01", "위기 가운데 언약의 안정과 신실", True),
        ("q02", "무너지기 전 심판과 경고", False),
        (
            "q03",
            "언약이 흔들릴 때 심판의 경고와 회복의 약속이 동시에 엮이는 성경 경로는 어디인가?",
            True,
        ),
    ]


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _measure_live(query: str, origin: str = "https://mkmlife.com") -> dict[str, Any]:
    url = f"{origin}/api/v1/magic-orb/insight?query={urllib.parse.quote(query)}"
    req = urllib.request.Request(url, headers={"User-Agent": LIVE_PROBE_UA})
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read()
            ms = (time.perf_counter() - t0) * 1000
            doc = json.loads(body.decode("utf-8"))
            payload = doc.get("payload") or {}
            return {
                "ok": resp.status == 200,
                "status": resp.status,
                "latency_ms": round(ms, 1),
                "source": doc.get("source"),
                "rag_count": len(payload.get("rag_evidence") or []),
                "bloom_nodes": (payload.get("graph_bloom") or {}).get("stats", {}).get("node_count"),
            }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc), "latency_ms": round((time.perf_counter() - t0) * 1000, 1)}


def main() -> int:
    rows = _load_rows()
    items: list[dict[str, Any]] = []
    for qid, query, expand in rows:
        if qid == "q01":
            router = _load(ROOT / "reports/question_logos_subgraph_router_sidecar_v1_latest.json")
            insight = _load(ROOT / "docs/final/artifacts/magic_orb_question_insight_v1_latest.json")
            bloom = _load(ROOT / "docs/final/artifacts/magic_orb_graph_bloom_v1_latest.json")
        else:
            router = _load(ROOT / f"reports/magic_orb_insight_by_query/router_{qid}_latest.json")
            insight = _load(ROOT / f"reports/magic_orb_insight_by_query/insight_{qid}_latest.json")
            bloom = _load(ROOT / f"reports/magic_orb_insight_by_query/bloom_{qid}_latest.json")

        rag = list((insight or {}).get("rag_evidence") or [])
        slots = list((insight or {}).get("structured_insight_slots") or [])
        bloom_stats = (bloom or {}).get("stats") or {}
        router_query = (router or {}).get("query")
        query_match = router_query == query if router else None

        items.append(
            {
                "query_id": qid,
                "query_ko": query,
                "expand_graph": expand,
                "router_query_match": query_match,
                "router": {
                    "bridges_matched": (router or {}).get("bridges_matched"),
                    "paths": len((router or {}).get("paths") or []),
                    "verse_ids": len((router or {}).get("verse_ids") or []),
                    "theme_lanes_active": (router or {}).get("theme_lanes_active"),
                    "bridge_selection": ((router or {}).get("policy") or {}).get("bridge_selection"),
                    "top_match_scores": sorted(
                        {p.get("match_score") for p in (router or {}).get("paths") or [] if isinstance(p, dict)},
                        reverse=True,
                    )[:5],
                },
                "insight": {
                    "rag_evidence_count": len(rag),
                    "rag_fusion": (insight or {}).get("rag_fusion"),
                    "structured_insight_slots": len(slots),
                    "subgraph_summary": (insight or {}).get("subgraph_summary"),
                    "sample_rag_source_ids": [r.get("source_id") for r in rag[:3]],
                },
                "graph_bloom": {
                    "node_count": bloom_stats.get("node_count"),
                    "edge_count": bloom_stats.get("edge_count"),
                },
            }
        )

    live: list[dict[str, Any]] = []
    for _qid, query, _ in rows:
        live.append({"query_ko": query, **_measure_live(query)})

    doc = {
        "schema": "magic_orb_insight_baseline_v0",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "batch_wall_s_approx": 10,
        "chain_caps": {
            "lod_node_cap": 48,
            "lod_edge_cap": 56,
            "rag_evidence_cap": 24,
            "top_bridges_default": 6,
        },
        "findings": [
            "Pre-computed JSON + token-overlap router; not full-graph realtime search.",
            "Router v1.1 multi_coverage_v1: KO particle stems + theme-lane composite bridge pick.",
            "q03 composite (언약+심판+회복) targets >=3 bridges; q04 chain (심판→언약 잔류) high-difficulty bench.",
            "q05 [HYPO] hubris/trade × volatility overlay; Logos-primary not Field trigger.",
            "q02 still highest single-theme fan-out.",
            "Router --query overrides gold query_id (fix v1).",
            "Publish -DeployMkmlife skips q01 chain unless -RebuildInsight (UTF-8 fixture query).",
            "ANN-lite skipped in chain (--skip-ann-lite).",
        ],
        "rows": items,
        "live_api": live,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(OUT), "rows": len(items)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
