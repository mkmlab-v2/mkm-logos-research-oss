#!/usr/bin/env python3
"""Phase B: raw drop deltas → research plane → Ollama shallow router trigger + explore lane bias."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_mkm_deep_research_router_index_v1 import (  # noqa: E402
    PLANE_SLKM,
    build_router_index,
    default_out_path,
    rows_from_markdown,
)
from scripts.build_mkm_raw_drop_delta_v1 import build_raw_drop_delta  # noqa: E402
from scripts.build_mkm_research_router_to_shallow_v1 import router_index_to_shallow  # noqa: E402

DEFAULT_OUT_DIR = ROOT / "docs" / "final" / "artifacts"
ROUTER_INDEX = ROOT / "scripts" / "build_mkm_deep_research_router_index_v1.py"
ROUTER_SHALLOW = ROOT / "scripts" / "build_mkm_research_router_to_shallow_v1.py"
HANDOFF = ROOT / "scripts" / "build_ollama_shallow_router_handoff_v1.py"

PLANE_LANE_PRIORITY: dict[str, list[str]] = {
    "research_memory": ["concept", "repo", "implementation"],
    "research_edge": ["implementation", "concept", "repo"],
    "research_benchmarks": ["concept", "implementation", "repo"],
    "research_meta": ["repo", "concept", "implementation"],
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _posix_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)


def aggregate_plane_hint(*, deltas: list[dict[str, Any]], fallback: str = "research_meta") -> str:
    votes = Counter(str(d.get("plane_hint") or fallback) for d in deltas)
    if not votes:
        return fallback
    return votes.most_common(1)[0][0]


def build_deltas_from_paths(
    *,
    raw_paths: list[Path],
    query: str,
    baseline_md: Path | None,
    use_ollama: bool,
) -> list[dict[str, Any]]:
    baseline_ids: set[str] = set()
    if baseline_md and baseline_md.is_file():
        from scripts.check_research_lit_review_citation_lock_v1 import extract_arxiv_ids

        baseline_ids = set(extract_arxiv_ids(baseline_md.read_text(encoding="utf-8", errors="replace")))
    out: list[dict[str, Any]] = []
    for path in raw_paths:
        out.append(
            build_raw_drop_delta(
                source_path=path,
                query=query,
                baseline_arxiv_ids=baseline_ids,
                use_ollama=use_ollama,
            )
        )
    return out


def build_trigger_router_index(
    *,
    merged_md: Path,
    query: str,
    plane_hint: str,
) -> dict[str, Any]:
    rows = rows_from_markdown(merged_md)
    router = build_router_index(query=query, rows=rows, source_path=merged_md)
    router["research_plane"] = plane_hint
    router["coordinates_slkm"] = PLANE_SLKM.get(plane_hint, PLANE_SLKM["research_meta"])
    router["lane_priority"] = PLANE_LANE_PRIORITY.get(plane_hint, PLANE_LANE_PRIORITY["research_meta"])
    router["trigger_source"] = "mkm_raw_drop_shallow_trigger_v1"
    return router


def default_trigger_out(*, topic_slug: str, out_dir: Path = DEFAULT_OUT_DIR) -> Path:
    return out_dir / f"{topic_slug}_raw_drop_shallow_trigger_latest.json"


def build_trigger_doc(
    *,
    topic_slug: str,
    query: str,
    merged_md: Path,
    deltas: list[dict[str, Any]],
    plane_hint: str,
    router_path: Path,
    shallow_path: Path,
    handoff_path: Path | None,
) -> dict[str, Any]:
    lane_priority = PLANE_LANE_PRIORITY.get(plane_hint, PLANE_LANE_PRIORITY["research_meta"])
    shallow = router_index_to_shallow(json.loads(router_path.read_text(encoding="utf-8")))
    return {
        "schema": "mkm_raw_drop_shallow_trigger_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "topic_slug": topic_slug,
        "query": query,
        "merged_md": _posix_path(merged_md),
        "research_plane": plane_hint,
        "lane_priority": lane_priority,
        "domain_tag": shallow.get("domain_tag"),
        "raw_drop_count": len(deltas),
        "raw_drop_paths": [str(d.get("source_path") or "") for d in deltas],
        "new_arxiv_ids": sorted({aid for d in deltas for aid in (d.get("new_arxiv_ids") or [])}),
        "overclaim_candidate_count": sum(len(d.get("overclaim_candidates") or []) for d in deltas),
        "router_index_path": _posix_path(router_path),
        "shallow_out": _posix_path(shallow_path),
        "handoff_out": _posix_path(handoff_path) if handoff_path else None,
        "deep_explore_command": (
            f'py scripts/mkm_deep_explore_v1.py --query "{query}" '
            f'--lane-priority {",".join(lane_priority)}'
        ),
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "reproduce": (
            f'py scripts/build_mkm_raw_drop_shallow_trigger_v1.py '
            f'--merged "{_posix_path(merged_md)}" --topic-slug {topic_slug}'
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Raw drop → shallow router trigger (Phase B)")
    parser.add_argument("--merged", type=Path, required=True)
    parser.add_argument("--topic-slug", required=True)
    parser.add_argument("--query", default="research raw drop shallow trigger")
    parser.add_argument("--raw-path", type=Path, action="append", default=[])
    parser.add_argument("--delta-json", type=Path, action="append", default=[])
    parser.add_argument("--plane-hint", default=None, help="Override aggregated research_plane")
    parser.add_argument("--use-ollama", action="store_true")
    parser.add_argument("--no-ollama", action="store_true")
    parser.add_argument("--skip-handoff", action="store_true")
    parser.add_argument("--router-out", type=Path, default=None)
    parser.add_argument("--shallow-out", type=Path, default=None)
    parser.add_argument("--handoff-out", type=Path, default=ROOT / "reports" / "mkm_research_router_handoff_v1_latest.json")
    parser.add_argument("--out-json", type=Path, default=None)
    args = parser.parse_args()

    merged_path = args.merged.resolve()
    if not merged_path.is_file():
        print(json.dumps({"ok": False, "error": f"missing merged: {merged_path}"}, ensure_ascii=False))
        return 2

    deltas: list[dict[str, Any]] = []
    for delta_path in args.delta_json:
        if delta_path.is_file():
            doc = json.loads(delta_path.read_text(encoding="utf-8"))
            if doc.get("schema") == "mkm_raw_drop_delta_v1":
                deltas.append(doc)
    if args.raw_path:
        use_ollama = bool(args.use_ollama and not args.no_ollama)
        deltas.extend(
            build_deltas_from_paths(
                raw_paths=[p.resolve() for p in args.raw_path],
                query=args.query,
                baseline_md=merged_path,
                use_ollama=use_ollama,
            )
        )
    if not deltas:
        print(json.dumps({"ok": False, "error": "provide --raw-path and/or --delta-json"}, ensure_ascii=False))
        return 2

    plane_hint = args.plane_hint or aggregate_plane_hint(deltas=deltas)
    router_doc = build_trigger_router_index(merged_md=merged_path, query=args.query, plane_hint=plane_hint)
    router_path = args.router_out.resolve() if args.router_out else default_out_path(merged_path)
    shallow_path = args.shallow_out.resolve() if args.shallow_out else DEFAULT_OUT_DIR / "mkm_research_router_shallow_v1_latest.json"
    router_path.parent.mkdir(parents=True, exist_ok=True)
    router_path.write_text(json.dumps(router_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    shallow = router_index_to_shallow(router_doc)
    shallow_path.parent.mkdir(parents=True, exist_ok=True)
    shallow_path.write_text(json.dumps(shallow, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    handoff_path: Path | None = None
    if not args.skip_handoff:
        handoff_path = args.handoff_out.resolve()
        proc = _run(
            [
                sys.executable,
                str(HANDOFF),
                "--input-json",
                str(shallow_path),
                "--out-json",
                str(handoff_path),
            ]
        )
        if proc.returncode != 0:
            print(json.dumps({"ok": False, "error": "handoff failed", "stderr": proc.stderr}, ensure_ascii=False))
            return proc.returncode

    trigger_out = args.out_json.resolve() if args.out_json else default_trigger_out(topic_slug=args.topic_slug)
    trigger_doc = build_trigger_doc(
        topic_slug=args.topic_slug,
        query=args.query,
        merged_md=merged_path,
        deltas=deltas,
        plane_hint=plane_hint,
        router_path=router_path,
        shallow_path=shallow_path,
        handoff_path=handoff_path,
    )
    trigger_out.parent.mkdir(parents=True, exist_ok=True)
    trigger_out.write_text(json.dumps(trigger_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "out_json": _posix_path(trigger_out),
                "research_plane": plane_hint,
                "domain_tag": trigger_doc["domain_tag"],
                "lane_priority": trigger_doc["lane_priority"],
                "raw_drop_count": len(deltas),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
