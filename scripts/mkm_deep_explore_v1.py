#!/usr/bin/env python3
"""MKM hybrid deep explore v1 (P0) — 3-lane parallel fetch + dedupe + raw JSONL.

Lanes:
  concept        — arXiv API (survey/benchmark/review bias)
  implementation — arXiv API (system/framework bias)
  repo           — local docs/research + docs/final (.md) + scripts (.py) crosswalk

Track B · research_only · send_gate HOLD · not a live DR agent replacement.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.check_research_lit_review_citation_lock_v1 import quote_hash_arxiv  # noqa: E402

DEFAULT_RAW_DIR = ROOT / "docs" / "research" / "raw"
DEFAULT_MANIFEST = ROOT / "reports" / "mkm_deep_explore_v1_latest.json"
ATOM_NS = "{http://www.w3.org/2005/Atom}"
ARXIV_API = "http://export.arxiv.org/api/query"
ROW_SCHEMA = "mkm_deep_explore_row_v1"
REPO_SCAN_SPECS: tuple[tuple[Path, tuple[str, ...]], ...] = (
    (ROOT / "scripts", ("*.py",)),
    (ROOT / "docs" / "research", ("*.md",)),
    (ROOT / "docs" / "final", ("*.md",)),
)
# CX4T: skip historical pin env trees and broken venv walks (immutable moonshot artifacts).
_REPO_SKIP_DIR_NAMES = frozenset(
    {".venv", "__pycache__", "node_modules", ".git", "site-packages", ".tox", ".mypy_cache"}
)
_REPO_SKIP_PREFIXES = (
    "docs/research/moonshot_pccc_gate0/gate0_5/pins/envs/",
)


def _should_skip_repo_path(path: Path) -> bool:
    rel = path.relative_to(ROOT).as_posix()
    if any(rel.startswith(prefix) for prefix in _REPO_SKIP_PREFIXES):
        return True
    return any(part in _REPO_SKIP_DIR_NAMES for part in path.parts)


def _iter_repo_scan_files(root: Path, pattern: str):
    """Safe rglob for repo lane — skip pin envs; tolerate broken symlink trees."""
    for dirpath, dirnames, filenames in os.walk(root, topdown=True, onerror=lambda _: None):
        cur = Path(dirpath)
        if _should_skip_repo_path(cur):
            dirnames.clear()
            continue
        dirnames[:] = [d for d in dirnames if not _should_skip_repo_path(cur / d)]
        if pattern.startswith("*."):
            suffix = pattern[1:]
            names = [n for n in filenames if n.endswith(suffix)]
        else:
            names = filenames
        for name in names:
            yield cur / name


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _utc_date() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def slugify_query(query: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", query.lower().strip())
    slug = slug.strip("_")
    return slug[:60] or "query"


def _normalize_arxiv_id(raw_id: str) -> str:
    aid = raw_id.rstrip("/").split("/abs/")[-1] if "/abs/" in raw_id else raw_id.strip()
    return re.sub(r"v\d+$", "", aid, flags=re.IGNORECASE)


def _parse_arxiv_atom(xml_bytes: bytes) -> list[dict[str, str]]:
    root = ET.fromstring(xml_bytes)
    rows: list[dict[str, str]] = []
    for entry in root.findall(f"{ATOM_NS}entry"):
        raw_id = entry.findtext(f"{ATOM_NS}id") or ""
        arxiv_id = _normalize_arxiv_id(raw_id)
        if not arxiv_id:
            continue
        title = (entry.findtext(f"{ATOM_NS}title") or "").strip().replace("\n", " ")
        summary = (entry.findtext(f"{ATOM_NS}summary") or "").strip().replace("\n", " ")[:400]
        rows.append(
            {
                "arxiv_id": arxiv_id,
                "title": title,
                "summary": summary,
                "url": f"https://arxiv.org/abs/{arxiv_id}",
            }
        )
    return rows


def _fetch_arxiv_search(search_query: str, *, max_results: int, timeout: float) -> list[dict[str, str]]:
    safe_query = urllib.parse.quote(search_query, safe=":+()")
    url = (
        f"{ARXIV_API}?search_query={safe_query}"
        f"&start=0&max_results={max_results}&sortBy=relevance&sortOrder=descending"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "mkm-deep-explore/1.0 (+research-only)"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return _parse_arxiv_atom(resp.read())


def _token_to_arxiv_clause(token: str) -> str:
    aliases = {
        "llm": "abs:LLM",
        "os": "abs:operating",
        "ai": "abs:artificial",
    }
    key = token.lower()
    if key in aliases:
        return aliases[key]
    return f"abs:{token}"


def build_lane_search_query(query: str, lane: str) -> str:
    tokens = [re.sub(r"[^\w\-]", "", t) for t in re.split(r"\s+", query.strip()) if t]
    if not tokens:
        tokens = ["research"]
    core_tokens = tokens[:4]
    if len(core_tokens) == 1:
        core = _token_to_arxiv_clause(core_tokens[0])
    else:
        core = "+OR+".join(_token_to_arxiv_clause(t) for t in core_tokens)
        core = f"({core})"
    if lane == "concept":
        return f"{core}+AND+(abs:survey+OR+abs:benchmark+OR+abs:review)"
    if lane == "implementation":
        return f"{core}+AND+(abs:implementation+OR+abs:system+OR+abs:framework)"
    return core


def _make_arxiv_row(
    *,
    lane: str,
    query: str,
    paper: dict[str, str],
    idx: int,
) -> dict[str, Any]:
    arxiv_id = paper["arxiv_id"]
    return {
        "schema": ROW_SCHEMA,
        "row_id": f"{lane}-arxiv-{idx:03d}",
        "lane": lane,
        "source": "arxiv_api_v1",
        "arxiv_id": arxiv_id,
        "quote_hash": quote_hash_arxiv(arxiv_id),
        "title": paper.get("title") or "",
        "summary": paper.get("summary") or "",
        "url": paper.get("url") or f"https://arxiv.org/abs/{arxiv_id}",
        "query": query,
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
    }


def lane_arxiv(query: str, lane: str, *, max_results: int, timeout: float) -> tuple[list[dict[str, Any]], str | None]:
    search_q = build_lane_search_query(query, lane)
    try:
        papers = _fetch_arxiv_search(search_q, max_results=max_results, timeout=timeout)
        if not papers and lane in {"concept", "implementation"}:
            fallback_q = build_lane_search_query(query, "core")
            papers = _fetch_arxiv_search(fallback_q, max_results=max_results, timeout=timeout)
    except (urllib.error.URLError, OSError, TimeoutError, ET.ParseError) as exc:
        return [], f"{lane}: {exc}"
    rows = [_make_arxiv_row(lane=lane, query=query, paper=p, idx=i + 1) for i, p in enumerate(papers)]
    return rows, None


def _query_tokens(query: str) -> list[str]:
    return [t.lower() for t in re.split(r"\s+", query.strip()) if len(t) >= 3]


def lane_repo(query: str, *, max_results: int) -> list[dict[str, Any]]:
    tokens = _query_tokens(query)
    if not tokens:
        tokens = ["research"]
    per_root = max(1, max_results // len(REPO_SCAN_SPECS))
    hits: list[dict[str, Any]] = []
    for root, patterns in REPO_SCAN_SPECS:
        if len(hits) >= max_results:
            break
        root_hits: list[dict[str, Any]] = []
        if not root.is_dir():
            continue
        for pattern in patterns:
            try:
                paths = sorted(_iter_repo_scan_files(root, pattern))
            except (FileNotFoundError, OSError):
                continue
            for path in paths:
                if len(root_hits) >= per_root or len(hits) + len(root_hits) >= max_results:
                    break
                if _should_skip_repo_path(path):
                    continue
                try:
                    text = path.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                lower = text.lower()
                matched = [t for t in tokens if t in lower]
                if len(matched) < min(2, len(tokens)):
                    continue
                rel = path.relative_to(ROOT).as_posix()
                root_hits.append(
                    {
                        "schema": ROW_SCHEMA,
                        "row_id": f"repo-{len(hits) + len(root_hits) + 1:03d}",
                        "lane": "repo",
                        "source": "mkm_repo_scan_v1",
                        "repo_path": rel,
                        "title": path.stem.replace("_", " "),
                        "matched_tokens": matched,
                        "url": f"file:///{rel}",
                        "query": query,
                        "research_only": True,
                        "send_gate": "HOLD",
                        "hypothesis_class": "HYPO",
                    }
                )
            if len(root_hits) >= per_root or len(hits) + len(root_hits) >= max_results:
                break
        hits.extend(root_hits)
    return hits[:max_results]


def dedupe_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen_arxiv: set[str] = set()
    seen_repo: set[str] = set()
    out: list[dict[str, Any]] = []
    for row in rows:
        aid = row.get("arxiv_id")
        if isinstance(aid, str) and aid:
            if aid in seen_arxiv:
                continue
            seen_arxiv.add(aid)
        repo_path = row.get("repo_path")
        if isinstance(repo_path, str) and repo_path:
            if repo_path in seen_repo:
                continue
            seen_repo.add(repo_path)
        out.append(row)
    return out


def _log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def order_rows_by_lane(rows: list[dict[str, Any]], lane_priority: list[str]) -> list[dict[str, Any]]:
    rank = {lane: idx for idx, lane in enumerate(lane_priority)}
    return sorted(rows, key=lambda row: rank.get(str(row.get("lane") or ""), 99))


def run_lanes_parallel(
    query: str,
    *,
    max_per_lane: int,
    timeout: float,
    offline: bool,
    lane_priority: list[str] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, int], list[str]]:
    errors: list[str] = []
    lane_rows: dict[str, list[dict[str, Any]]] = {"concept": [], "implementation": [], "repo": []}

    if offline:
        _log("mkm_deep_explore: lane repo (offline mode)")
        lane_rows["repo"] = lane_repo(query, max_results=max_per_lane)
        stats = {k: len(v) for k, v in lane_rows.items()}
        merged = dedupe_rows(lane_rows["concept"] + lane_rows["implementation"] + lane_rows["repo"])
        if lane_priority:
            merged = order_rows_by_lane(merged, lane_priority)
        return merged, stats, errors

    _log("mkm_deep_explore: lanes concept+implementation (arXiv) + repo in parallel")
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {
            pool.submit(lane_arxiv, query, "concept", max_results=max_per_lane, timeout=timeout): "concept",
            pool.submit(
                lane_arxiv, query, "implementation", max_results=max_per_lane, timeout=timeout
            ): "implementation",
            pool.submit(lane_repo, query, max_results=max_per_lane): "repo",
        }
        for fut in as_completed(futures):
            name = futures[fut]
            if name == "repo":
                lane_rows[name] = fut.result()
                continue
            rows, err = fut.result()
            lane_rows[name] = rows
            if err:
                errors.append(err)
            _log(f"mkm_deep_explore: lane {name} done ({len(lane_rows[name])} rows)")

    stats = {k: len(v) for k, v in lane_rows.items()}
    merged = dedupe_rows(lane_rows["concept"] + lane_rows["implementation"] + lane_rows["repo"])
    if lane_priority:
        merged = order_rows_by_lane(merged, lane_priority)
    return merged, stats, errors


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")


def write_md_stub(path: Path, query: str, rows: list[dict[str, Any]]) -> None:
    arxiv_rows = [r for r in rows if r.get("arxiv_id")]
    lines = [
        f"# MKM deep explore stub — {query}",
        "",
        f"**Generated:** {_utc_now()} · **Track:** B-track · `research_only`",
        "",
        "## arXiv catalog (FACT-lite input)",
        "",
        "| arXiv ID | Lane | Title |",
        "|----------|------|-------|",
    ]
    for row in arxiv_rows:
        aid = row.get("arxiv_id", "")
        title = str(row.get("title") or "").replace("|", "/")[:80]
        lines.append(f"| {aid} | {row.get('lane', '')} | {title} |")
    if not arxiv_rows:
        lines.append("| — | — | (no arxiv rows) |")
    lines.extend(["", f"*Verify:* `py scripts/check_research_lit_review_citation_lock_v1.py --input {path.as_posix()}`", ""])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_manifest(
    *,
    query: str,
    slug: str,
    rows: list[dict[str, Any]],
    lane_stats: dict[str, int],
    errors: list[str],
    raw_jsonl: Path,
    md_stub: Path | None,
    lane_priority: list[str] | None = None,
) -> dict[str, Any]:
    arxiv_ids = [r["arxiv_id"] for r in rows if r.get("arxiv_id")]
    lanes = lane_priority or ["concept", "implementation", "repo"]
    return {
        "schema": "mkm_deep_explore_run_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "query": query,
        "query_slug": slug,
        "lanes": lanes,
        "lane_priority": lanes,
        "lane_stats": lane_stats,
        "deduped_count": len(rows),
        "arxiv_id_count": len(arxiv_ids),
        "raw_jsonl": raw_jsonl.relative_to(ROOT).as_posix(),
        "md_stub": md_stub.relative_to(ROOT).as_posix() if md_stub else None,
        "fetch_errors": errors,
        "research_only": True,
        "send_gate": "HOLD",
        "citation_lock_command": (
            f"py scripts/check_research_lit_review_citation_lock_v1.py --input {md_stub.relative_to(ROOT).as_posix()}"
            if md_stub
            else None
        ),
        "reproduce": f'py scripts/mkm_deep_explore_v1.py --query "{query}"',
    }


def explore(
    query: str,
    *,
    max_per_lane: int,
    timeout: float,
    offline: bool,
    raw_dir: Path,
    write_md: bool,
    lane_priority: list[str] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]], bool]:
    slug = slugify_query(query)
    date = _utc_date()
    raw_jsonl = raw_dir / f"{slug}_explore_{date}.jsonl"
    md_stub = raw_dir / f"{slug}_explore_{date}.md" if write_md else None

    rows, lane_stats, errors = run_lanes_parallel(
        query,
        max_per_lane=max_per_lane,
        timeout=timeout,
        offline=offline,
        lane_priority=lane_priority,
    )
    manifest = build_manifest(
        query=query,
        slug=slug,
        rows=rows,
        lane_stats=lane_stats,
        errors=errors,
        raw_jsonl=raw_jsonl,
        md_stub=md_stub,
        lane_priority=lane_priority,
    )
    manifest["ok"] = len(rows) > 0
    return manifest, rows, manifest["ok"]


def main() -> int:
    parser = argparse.ArgumentParser(description="MKM 3-lane deep explore v1 (P0 skeleton)")
    parser.add_argument("--query", required=True, help="Research topic query string")
    parser.add_argument("--max-per-lane", type=int, default=8, help="Max hits per lane")
    parser.add_argument("--min-rows", type=int, default=1, help="Minimum deduped rows to pass")
    parser.add_argument("--timeout-sec", type=float, default=25.0)
    parser.add_argument("--offline", action="store_true", help="Repo lane only (no arXiv network)")
    parser.add_argument("--dry-run", action="store_true", help="Fetch only; do not write files")
    parser.add_argument("--no-md-stub", action="store_true", help="Skip markdown stub for citation_lock")
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--manifest-json", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--lane-priority", default=None, help="Comma lane order, e.g. concept,repo,implementation")
    parser.add_argument("--trigger-json", type=Path, default=None, help="mkm_raw_drop_shallow_trigger_v1 artifact")
    args = parser.parse_args()

    lane_priority: list[str] | None = None
    if args.trigger_json and args.trigger_json.is_file():
        trigger = json.loads(args.trigger_json.read_text(encoding="utf-8"))
        if isinstance(trigger.get("lane_priority"), list):
            lane_priority = [str(x) for x in trigger["lane_priority"]]
    if args.lane_priority:
        lane_priority = [x.strip() for x in args.lane_priority.split(",") if x.strip()]

    write_md = not args.no_md_stub
    _log(f"mkm_deep_explore: query={args.query!r} offline={args.offline} dry_run={args.dry_run}")
    manifest, rows, has_rows = explore(
        args.query,
        max_per_lane=args.max_per_lane,
        timeout=args.timeout_sec,
        offline=args.offline,
        raw_dir=args.raw_dir.resolve(),
        write_md=write_md,
        lane_priority=lane_priority,
    )

    ok = has_rows and manifest["deduped_count"] >= args.min_rows
    manifest["ok"] = ok
    print(json.dumps({k: manifest[k] for k in manifest if k != "ok"} | {"ok": ok}, ensure_ascii=False))

    if args.dry_run:
        return 0 if ok else 1

    if not ok:
        return 1

    slug = manifest["query_slug"]
    date = _utc_date()
    raw_jsonl = args.raw_dir.resolve() / f"{slug}_explore_{date}.jsonl"
    write_jsonl(raw_jsonl, rows)
    if write_md:
        md_path = args.raw_dir.resolve() / f"{slug}_explore_{date}.md"
        write_md_stub(md_path, args.query, rows)
        manifest["md_stub"] = md_path.relative_to(ROOT).as_posix()
        manifest["citation_lock_command"] = (
            f"py scripts/check_research_lit_review_citation_lock_v1.py --input {manifest['md_stub']}"
        )

    man_path = args.manifest_json.resolve()
    man_path.parent.mkdir(parents=True, exist_ok=True)
    man_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
