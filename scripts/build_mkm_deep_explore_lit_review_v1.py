#!/usr/bin/env python3
"""Build Tier-1 LIT_REVIEW markdown from mkm_deep_explore_v1 JSONL rows."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.check_research_lit_review_citation_lock_v1 import quote_hash_arxiv  # noqa: E402
from scripts.mkm_deep_explore_v1 import slugify_query  # noqa: E402

DEFAULT_RESEARCH_DIR = ROOT / "docs" / "research"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _utc_date() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _posix_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def lit_review_path(*, query: str, date: str | None = None, research_dir: Path = DEFAULT_RESEARCH_DIR) -> Path:
    slug = slugify_query(query)
    day = date or _utc_date()
    return research_dir / f"{slug}_LIT_REVIEW_{day}.md"


def build_lit_review_markdown(
    *,
    query: str,
    rows: list[dict[str, Any]],
    source_jsonl: Path,
) -> str:
    arxiv_rows = [r for r in rows if r.get("arxiv_id")]
    repo_rows = [r for r in rows if r.get("repo_path")]
    lane_stats = {
        "concept": sum(1 for r in rows if r.get("lane") == "concept"),
        "implementation": sum(1 for r in rows if r.get("lane") == "implementation"),
        "repo": sum(1 for r in rows if r.get("lane") == "repo"),
    }
    rel_jsonl = _posix_path(source_jsonl)

    lines = [
        f"# {query} — MKM LIT_REVIEW (explore P1) [HYPO]",
        "",
        f"**Generated:** {_utc_now()} · **Skill:** mkm-deep-research · **Tier:** 1 (explore→LIT_REVIEW)",
        f"**Track:** B-track · `research_only` · `send_gate: HOLD`",
        f"**Source JSONL:** `{rel_jsonl}`",
        "",
        "## Executive summary",
        "",
        f"- **3-lane explore:** concept={lane_stats['concept']} · "
        f"implementation={lane_stats['implementation']} · repo={lane_stats['repo']}",
        f"- **Unique arXiv IDs:** {len(arxiv_rows)} (FACT-lite Phase A target)",
        "- **Next:** Cursor distiller → MKM schema/bench deltas · Tier 2 pytest",
        "",
        "---",
        "",
        "## Paper catalog (arXiv)",
        "",
        "| # | arXiv ID | Lane | Title |",
        "|---|----------|------|-------|",
    ]
    for i, row in enumerate(arxiv_rows, start=1):
        aid = str(row.get("arxiv_id") or "")
        title = re.sub(r"\s+", " ", str(row.get("title") or "")).replace("|", "/")[:100]
        lines.append(f"| {i} | {aid} | {row.get('lane', '')} | {title} |")
    if not arxiv_rows:
        lines.append("| — | — | — | (no arxiv rows) |")

    lines.extend(
        [
            "",
            "## Repo crosswalk (MKM)",
            "",
            "| # | Path | Matched tokens |",
            "|---|------|----------------|",
        ]
    )
    for i, row in enumerate(repo_rows, start=1):
        path = str(row.get("repo_path") or "")
        tokens = ", ".join(row.get("matched_tokens") or [])
        lines.append(f"| {i} | `{path}` | {tokens} |")
    if not repo_rows:
        lines.append("| — | — | — |")

    lines.extend(
        [
            "",
            "## MKM mapping (P1 stub)",
            "",
            "| Artifact | Map | Tag |",
            "|----------|-----|-----|",
            "| `ollama_shallow_router_output_v1` | lane routing hints | `[Needs experiment]` |",
            "| `check_research_lit_review_citation_lock_v1.py` | arXiv existence gate | `[Adoptable now]` |",
            "| `semantic_rag_bridge_insight_bundle_v1` | deep handoff inject | `[Needs experiment]` |",
            "",
            "## Reproducibility",
            "",
            "```powershell",
            f"py scripts/mkm_deep_explore_v1.py --query \"{query}\"",
            f"py scripts/build_mkm_deep_explore_lit_review_v1.py --jsonl {rel_jsonl} --query \"{query}\"",
            "py scripts/check_research_lit_review_citation_lock_v1.py --input docs/research/<this-file>.md",
            "```",
            "",
            "*Classification: B-track · Not legal advice · Track A live LOCKED*",
            "",
        ]
    )
    return "\n".join(lines)


def write_lit_review(
    *,
    query: str,
    rows: list[dict[str, Any]],
    source_jsonl: Path,
    out_path: Path | None = None,
) -> Path:
    target = out_path or lit_review_path(query=query)
    target.parent.mkdir(parents=True, exist_ok=True)
    # refresh quote_hash on write
    for row in rows:
        aid = row.get("arxiv_id")
        if isinstance(aid, str) and aid:
            row["quote_hash"] = quote_hash_arxiv(aid)
    target.write_text(
        build_lit_review_markdown(query=query, rows=rows, source_jsonl=source_jsonl),
        encoding="utf-8",
    )
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description="Build LIT_REVIEW md from explore JSONL")
    parser.add_argument("--jsonl", type=Path, required=True, help="Input explore JSONL")
    parser.add_argument("--query", required=True, help="Original explore query")
    parser.add_argument("--out", type=Path, default=None, help="Output LIT_REVIEW md path")
    parser.add_argument("--stdout-only", action="store_true")
    args = parser.parse_args()

    jsonl_path = args.jsonl.resolve()
    if not jsonl_path.is_file():
        print(json.dumps({"ok": False, "error": f"missing jsonl: {jsonl_path}"}), file=sys.stderr)
        return 2

    rows = load_jsonl(jsonl_path)
    if not rows:
        print(json.dumps({"ok": False, "error": "empty jsonl"}), file=sys.stderr)
        return 1

    out_path = write_lit_review(
        query=args.query,
        rows=rows,
        source_jsonl=jsonl_path,
        out_path=args.out.resolve() if args.out else None,
    )
    payload = {
        "ok": True,
        "out_path": _posix_path(out_path),
        "row_count": len(rows),
        "arxiv_id_count": sum(1 for r in rows if r.get("arxiv_id")),
    }
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
