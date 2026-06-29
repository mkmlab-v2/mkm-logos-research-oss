#!/usr/bin/env python3
"""Verify LTM graph concept coordinates match index filter allowlist ([HYPO] / B-track).

  py scripts/check_ltm_index_filter_v1.py
  py scripts/check_ltm_index_filter_v1.py --path scripts/foo.py
"""
from __future__ import annotations

import argparse
import json
import sys
from fnmatch import fnmatch
from pathlib import Path, PurePosixPath

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_ROOT / "scripts"))

from mkm_long_term_memory_graph_lib_v1 import (  # noqa: E402
    CONCEPT_SPECS,
    DEFAULT_GRAPH_PATH,
    load_graph,
)

DEFAULT_FILTER = (
    SCRIPT_ROOT / "docs" / "final" / "artifacts" / "ltm_index_filter_v1.json"
)


def _norm_posix(path: str) -> str:
    return PurePosixPath(path.replace("\\", "/")).as_posix()


def _glob_match(rel: str, pattern: str) -> bool:
    rel = _norm_posix(rel)
    pattern = _norm_posix(pattern)
    if fnmatch(rel, pattern):
        return True
    try:
        if PurePosixPath(rel).match(pattern):
            return True
    except ValueError:
        pass
    if pattern in ("**/.git/**", ".git/**"):
        return "/.git/" in f"/{rel}/" or rel.startswith(".git/")
    if "**" in pattern:
        head, tail = pattern.split("**", 1)
        head = head.rstrip("/")
        if head and not (rel == head or rel.startswith(f"{head}/")):
            return False
        suffix = rel[len(head) :].lstrip("/") if head else rel
        tail = tail.lstrip("/") or "*"
        if fnmatch(suffix, tail):
            return True
        try:
            return PurePosixPath(suffix).match(tail)
        except ValueError:
            return False
    return False


def _matches_any(rel: str, patterns: list[str]) -> bool:
    return any(_glob_match(rel, pat) for pat in patterns)


def path_allowed_by_filter(rel: str, filter_doc: dict) -> bool:
    """True when path is not hard-excluded and matches preferred include (if any)."""
    rel = _norm_posix(rel)
    hard_exclude = list(filter_doc.get("hard_exclude_globs") or [])
    preferred = list(filter_doc.get("preferred_include_globs") or [])
    if _matches_any(rel, hard_exclude):
        return False
    if preferred:
        return _matches_any(rel, preferred)
    return True


def path_allowed(rel: str, *, include: list[str], exclude: list[str]) -> bool:
    """Legacy helper — prefer check_concept_paths hard/discouraged split."""
    rel = _norm_posix(rel)
    if _matches_any(rel, exclude):
        return False
    return _matches_any(rel, include)


def load_filter(path: Path) -> dict:
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    if doc.get("schema") != "ltm_index_filter_v1":
        raise ValueError(f"unexpected filter schema: {doc.get('schema')!r}")
    return doc


def check_concept_paths(
    root: Path,
    *,
    filter_doc: dict,
    extra_paths: list[str] | None = None,
    strict_discouraged: bool = False,
) -> tuple[list[str], list[str]]:
    hard_exclude = list(filter_doc.get("hard_exclude_globs") or [])
    discouraged = list(filter_doc.get("discouraged_globs") or [])
    preferred = list(filter_doc.get("preferred_include_globs") or [])
    errors: list[str] = []
    warnings: list[str] = []
    paths_to_check: list[tuple[str, str]] = []

    for spec in CONCEPT_SPECS:
        for coord in spec.coordinates:
            rel = _norm_posix(coord.file_path)
            paths_to_check.append((spec.concept_id, rel))

    for rel in extra_paths or []:
        paths_to_check.append(("--path", _norm_posix(rel)))

    seen: set[str] = set()
    for concept_id, rel in paths_to_check:
        key = f"{concept_id}:{rel}"
        if key in seen:
            continue
        seen.add(key)
        if _matches_any(rel, hard_exclude):
            errors.append(f"{concept_id}: hard_exclude path: {rel}")
            continue
        if not (root / rel).is_file():
            errors.append(f"{concept_id}: file missing: {rel}")
            continue
        if _matches_any(rel, discouraged):
            msg = f"{concept_id}: discouraged churn path: {rel}"
            if strict_discouraged:
                errors.append(msg)
            else:
                warnings.append(msg)
        elif preferred and not _matches_any(rel, preferred):
            warnings.append(f"{concept_id}: not in preferred_include: {rel}")
    return errors, warnings


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspace-root", type=Path, default=SCRIPT_ROOT)
    ap.add_argument("--filter", type=Path, default=DEFAULT_FILTER)
    ap.add_argument("--path", action="append", default=[], help="Extra path to validate")
    ap.add_argument(
        "--strict-discouraged",
        action="store_true",
        help="Treat discouraged churn paths (reports/*_latest) as errors",
    )
    ap.add_argument(
        "--require-graph-sync",
        action="store_true",
        help="Fail if graph JSON concept count != CONCEPT_SPECS count",
    )
    args = ap.parse_args()

    root = args.workspace_root.resolve()
    if not args.filter.is_file():
        print(f"FAIL: filter missing: {args.filter}", file=sys.stderr)
        return 1

    try:
        filter_doc = load_filter(args.filter)
    except (json.JSONDecodeError, ValueError) as exc:
        print(f"FAIL: filter load: {exc}", file=sys.stderr)
        return 1

    errors, warnings = check_concept_paths(
        root,
        filter_doc=filter_doc,
        extra_paths=args.path,
        strict_discouraged=args.strict_discouraged,
    )
    if args.require_graph_sync and DEFAULT_GRAPH_PATH.is_file():
        graph = load_graph(DEFAULT_GRAPH_PATH)
        if int(graph.get("concept_count") or 0) != len(CONCEPT_SPECS):
            errors.append(
                "graph concept_count drift vs CONCEPT_SPECS — rebuild graph"
            )

    if errors:
        for err in errors:
            print(f"FAIL: {err}", file=sys.stderr)
        return 1

    for warn in warnings[:20]:
        print(f"WARN: {warn}", file=sys.stderr)
    if len(warnings) > 20:
        print(f"WARN: ... +{len(warnings) - 20} more discouraged paths", file=sys.stderr)

    print(
        f"ltm_index_filter_v1: OK ({len(CONCEPT_SPECS)} concept paths, "
        f"warnings={len(warnings)})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
