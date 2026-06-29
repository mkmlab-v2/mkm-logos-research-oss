#!/usr/bin/env python3
"""Build research router index from explore JSONL or MERGED/LIT_REVIEW markdown catalog."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.check_research_lit_review_fact_support_v1 import extract_claims_from_markdown  # noqa: E402
from scripts.mkm_deep_explore_v1 import slugify_query  # noqa: E402

DEFAULT_OUT_DIR = ROOT / "docs" / "final" / "artifacts"

PLANE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "research_benchmarks": (
        "benchmark",
        "bench",
        "eval",
        "fact",
        "race",
        "metric",
        "score",
        "routerbench",
        "citation",
        "verification",
    ),
    "research_memory": ("memory", "memgpt", "rag", "retrieval", "context", "vector", "hipporag"),
    "research_edge": ("edge", "cloud", "federated", "slm", "collaborative", "on-device", "hybrid"),
    "research_meta": ("agent", "orchestration", "skill", "mcp", "research", "deep", "dr"),
}

PLANE_SLKM: dict[str, dict[str, float]] = {
    "research_benchmarks": {"S": 0.15, "L": 0.20, "K": 0.45, "M": 0.20},
    "research_memory": {"S": 0.20, "L": 0.25, "K": 0.20, "M": 0.35},
    "research_edge": {"S": 0.35, "L": 0.30, "K": 0.20, "M": 0.15},
    "research_meta": {"S": 0.25, "L": 0.25, "K": 0.25, "M": 0.25},
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _posix_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def rows_from_markdown(md_path: Path) -> list[dict[str, Any]]:
    claims = extract_claims_from_markdown(md_path.read_text(encoding="utf-8", errors="replace"))
    return [
        {
            "arxiv_id": claim["arxiv_id"],
            "title": claim["claim"],
            "lane": claim.get("lane") or "catalog",
        }
        for claim in claims
    ]


def classify_research_plane(*, query: str, rows: list[dict[str, Any]]) -> str:
    blob_parts = [query.lower()]
    for row in rows:
        blob_parts.append(str(row.get("title") or "").lower())
        blob_parts.extend(str(t).lower() for t in (row.get("matched_tokens") or []))
    blob = " ".join(blob_parts)
    scores = {plane: sum(1 for kw in kws if kw in blob) for plane, kws in PLANE_KEYWORDS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "research_meta"


def lane_priority(rows: list[dict[str, Any]]) -> list[str]:
    counts = Counter(str(r.get("lane") or "") for r in rows if r.get("lane"))
    order = ["concept", "implementation", "repo", "catalog"]
    ranked = sorted(counts.keys(), key=lambda lane: (-counts[lane], order.index(lane) if lane in order else 99))
    return ranked or order


def build_router_index(
    *,
    query: str,
    rows: list[dict[str, Any]],
    source_path: Path,
) -> dict[str, Any]:
    plane = classify_research_plane(query=query, rows=rows)
    arxiv_ids = sorted({str(r["arxiv_id"]) for r in rows if r.get("arxiv_id")})
    repo_anchors = [
        str(r["repo_path"])
        for r in rows
        if r.get("repo_path") and str(r["repo_path"]).startswith("docs/")
    ]
    if not repo_anchors and str(source_path).endswith(".md"):
        repo_anchors = [_posix_path(source_path)]
    repo_anchors = repo_anchors[:3]
    lane_stats = dict(Counter(str(r.get("lane") or "") for r in rows if r.get("lane")))
    return {
        "schema": "mkm_deep_research_router_index_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "query": query,
        "query_slug": slugify_query(query),
        "source_path": _posix_path(source_path),
        "source_jsonl": _posix_path(source_path),
        "research_plane": plane,
        "lane_priority": lane_priority(rows),
        "lane_stats": lane_stats,
        "coordinates_slkm": PLANE_SLKM[plane],
        "anchor_ids": repo_anchors,
        "arxiv_ids": arxiv_ids,
        "row_count": len(rows),
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "policy": "Deterministic research routing index; optional Ollama shallow handoff input",
        "deep_fetch_next": [
            "scripts/build_mkm_research_router_to_shallow_v1.py",
            "scripts/check_research_lit_review_fact_support_v1.py",
        ],
    }


def default_out_path(source: Path, out_dir: Path = DEFAULT_OUT_DIR) -> Path:
    if source.suffix == ".md":
        return out_dir / f"{source.stem}_research_router_index_latest.json"
    return out_dir / f"{slugify_query(source.stem)}_research_router_index_latest.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build research router index from explore JSONL or LIT_REVIEW md")
    parser.add_argument("--jsonl", type=Path, default=None)
    parser.add_argument("--input-md", type=Path, default=None)
    parser.add_argument("--query", required=True)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--stdout-only", action="store_true")
    args = parser.parse_args()

    if bool(args.jsonl) == bool(args.input_md):
        print(json.dumps({"ok": False, "error": "provide exactly one of --jsonl or --input-md"}, ensure_ascii=False), file=sys.stderr)
        return 2

    if args.jsonl:
        source_path = args.jsonl.resolve()
        if not source_path.is_file():
            print(json.dumps({"ok": False, "error": f"missing jsonl: {source_path}"}), file=sys.stderr)
            return 2
        rows = load_jsonl(source_path)
    else:
        source_path = args.input_md.resolve()
        if not source_path.is_file():
            print(json.dumps({"ok": False, "error": f"missing md: {source_path}"}), file=sys.stderr)
            return 2
        rows = rows_from_markdown(source_path)

    if not rows:
        print(json.dumps({"ok": False, "error": "no catalog rows found"}, ensure_ascii=False), file=sys.stderr)
        return 1

    doc = build_router_index(query=args.query, rows=rows, source_path=source_path)
    out_path = args.out.resolve() if args.out else default_out_path(source_path)
    if not args.stdout_only:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    doc["out_path"] = _posix_path(out_path)
    print(
        json.dumps(
            {
                "ok": True,
                "out_path": doc["out_path"],
                "research_plane": doc["research_plane"],
                "row_count": doc["row_count"],
                "arxiv_id_count": len(doc["arxiv_ids"]),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
