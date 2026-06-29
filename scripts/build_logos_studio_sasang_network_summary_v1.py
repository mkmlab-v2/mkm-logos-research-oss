#!/usr/bin/env python3
"""Build lightweight Studio summary for sasang+logos routing network (B-track)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_GRAPH = ROOT / "docs/final/artifacts/logos_corpus_sasang_routing_graph_bundle_v1_latest.json"
DEFAULT_EDGE_QUALITY = ROOT / "reports/logos_corpus_sasang_edge_join_quality_v1_latest.json"
DEFAULT_BLOOM = ROOT / "docs/final/artifacts/logos_studio_31k_bloom_secondary_fetch_v1_latest.json"
DEFAULT_STUB = ROOT / "reports/logos_bloom_chapter_stub_merge_v1_latest.json"
DEFAULT_AUDIT = ROOT / "docs/final/artifacts/showroom_logos_subgraph_audit_slice_v1_latest.json"
DEFAULT_OUT_PUBLIC = ROOT / "projects/no1kmedi/public/data/logos_studio/sasang_network_summary_v1.json"
DEFAULT_OUT_ART = ROOT / "docs/final/artifacts/logos_studio_sasang_network_summary_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        row = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return row if isinstance(row, dict) else {}


def build_summary(
    *,
    graph_path: Path,
    edge_quality_path: Path,
    bloom_path: Path,
    stub_path: Path,
    audit_path: Path,
) -> dict[str, Any]:
    graph = _load(graph_path)
    eq = _load(edge_quality_path)
    bloom = _load(bloom_path)
    stub = _load(stub_path)
    audit = _load(audit_path)

    overlap = graph.get("graph_overlap") or {}
    summary = eq.get("summary") or {}
    edge_rows = list(eq.get("edge_type_quality") or [])
    weakest_parse = sorted(
        [r for r in edge_rows if isinstance(r, dict)],
        key=lambda r: (float(r.get("parse_ratio") or 0.0), float(r.get("touch_ratio") or 0.0)),
    )[:8]

    return {
        "schema": "logos_studio_sasang_network_summary_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "send_gate": "HOLD",
        "track_a_blocked": True,
        "headline": {
            "corpus_verse_count": int(graph.get("corpus_verse_count") or 0),
            "edges_touching_corpus": int(overlap.get("meaning_graph_edges_touching_corpus") or 0),
            "edge_touch_ratio": float(summary.get("edge_touch_ratio") or 0.0),
            "path_count_showroom": int(((audit.get("router_snapshot") or {}).get("path_count") or 0)),
            "bloom_chapter_shards": int(bloom.get("chapter_shard_count") or 0),
        },
        "cards": [
            {
                "id": "coverage",
                "title": "Corpus Coverage",
                "value": f"{int(graph.get('corpus_verse_count') or 0):,}",
                "note": "31k verse routing overlay rows",
            },
            {
                "id": "edge_touch",
                "title": "Edge Join Touch",
                "value": f"{float(summary.get('edge_touch_ratio') or 0.0):.2%}",
                "note": f"{int(summary.get('edges_touching_corpus') or 0):,} / {int(summary.get('edge_total') or 0):,}",
            },
            {
                "id": "showroom_paths",
                "title": "Showroom Paths",
                "value": str(int(((audit.get("router_snapshot") or {}).get("path_count") or 0))),
                "note": "public audit slice path count",
            },
            {
                "id": "bloom_shards",
                "title": "Bloom Shards",
                "value": str(int(bloom.get("chapter_shard_count") or 0)),
                "note": "secondary fetch chapter shards",
            },
        ],
        "drilldown": {
            "edge_quality": {
                "edge_total": int(summary.get("edge_total") or 0),
                "edges_touching_corpus": int(summary.get("edges_touching_corpus") or 0),
                "malformed_no_ref_count": int(summary.get("malformed_no_ref_count") or 0),
                "edge_type_quality": [
                    {
                        "edge_type": str(r.get("edge_type") or "unknown"),
                        "total": int(r.get("total") or 0),
                        "touch_ratio": float(r.get("touch_ratio") or 0.0),
                        "parse_ratio": float(r.get("parse_ratio") or 0.0),
                        "any_parse_ratio": float(r.get("any_parse_ratio") or 0.0),
                        "single_side_parse_ratio": float(r.get("single_side_parse_ratio") or 0.0),
                        "src_parse_ratio": float(r.get("src_parse_ratio") or 0.0),
                        "dst_parse_ratio": float(r.get("dst_parse_ratio") or 0.0),
                    }
                    for r in edge_rows
                    if isinstance(r, dict)
                ],
                "weakest_parse_edge_types": [
                    {
                        "edge_type": str(r.get("edge_type") or "unknown"),
                        "total": int(r.get("total") or 0),
                        "touch_ratio": float(r.get("touch_ratio") or 0.0),
                        "parse_ratio": float(r.get("parse_ratio") or 0.0),
                    }
                    for r in weakest_parse
                ],
            }
        },
        "sources": {
            "graph_bundle": str(graph_path.relative_to(ROOT)).replace("\\", "/") if graph_path.is_file() else str(graph_path),
            "edge_quality_report": str(edge_quality_path.relative_to(ROOT)).replace("\\", "/") if edge_quality_path.is_file() else str(edge_quality_path),
            "bloom_index": str(bloom_path.relative_to(ROOT)).replace("\\", "/") if bloom_path.is_file() else str(bloom_path),
            "stub_merge_report": str(stub_path.relative_to(ROOT)).replace("\\", "/") if stub_path.is_file() else str(stub_path),
            "showroom_audit_slice": str(audit_path.relative_to(ROOT)).replace("\\", "/") if audit_path.is_file() else str(audit_path),
        },
        "flags": {
            "stub_merge_skipped": bool(stub.get("skipped") is True),
            "non_gating": bool(graph.get("non_gating", True)),
            "forbidden_merge_active": bool(graph.get("must_not_merge_into")),
        },
        "disclaimer_ko": "Studio 요약은 B-track 관측 대시보드용. 투자/임상/Track A 트리거가 아니다.",
        "reproduce": "py scripts/build_logos_studio_sasang_network_summary_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--graph-bundle", type=Path, default=DEFAULT_GRAPH)
    ap.add_argument("--edge-quality-report", type=Path, default=DEFAULT_EDGE_QUALITY)
    ap.add_argument("--bloom-index", type=Path, default=DEFAULT_BLOOM)
    ap.add_argument("--stub-merge-report", type=Path, default=DEFAULT_STUB)
    ap.add_argument("--showroom-audit-slice", type=Path, default=DEFAULT_AUDIT)
    ap.add_argument("--out-public", type=Path, default=DEFAULT_OUT_PUBLIC)
    ap.add_argument("--out-artifact", type=Path, default=DEFAULT_OUT_ART)
    args = ap.parse_args()

    doc = build_summary(
        graph_path=args.graph_bundle,
        edge_quality_path=args.edge_quality_report,
        bloom_path=args.bloom_index,
        stub_path=args.stub_merge_report,
        audit_path=args.showroom_audit_slice,
    )

    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    args.out_public.parent.mkdir(parents=True, exist_ok=True)
    args.out_artifact.parent.mkdir(parents=True, exist_ok=True)
    args.out_public.write_text(payload, encoding="utf-8")
    args.out_artifact.write_text(payload, encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "corpus_verse_count": doc["headline"]["corpus_verse_count"],
                "edge_touch_ratio": doc["headline"]["edge_touch_ratio"],
                "out_public": str(args.out_public),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
