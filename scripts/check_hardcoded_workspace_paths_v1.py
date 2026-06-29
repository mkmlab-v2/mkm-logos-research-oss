#!/usr/bin/env python3
"""Detect hardcoded C:\\workspace paths — Launch Gate #1 audit [HYPO/OSS].

  py scripts/check_hardcoded_workspace_paths_v1.py --scope oss
  py scripts/check_hardcoded_workspace_paths_v1.py --scope oss --strict
  py scripts/check_hardcoded_workspace_paths_v1.py --scope all --out reports/...
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/hardcoded_workspace_paths_audit_v1_latest.json"

PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("c_backslash_workspace", re.compile(r"C:\\workspace", re.IGNORECASE)),
    ("c_slash_workspace", re.compile(r"C:/workspace", re.IGNORECASE)),
]

SKIP_DIR_NAMES = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    "build",
    ".pytest_cache",
    ".mypy_cache",
    ".cursor",
}

SKIP_REL_PREFIXES = (
    "reports/",
    "projects/bitcoin-trading/memory/",
    "projects/bitcoin-trading/exports/",
    "storage/",
    "build/",
    "memory/",
)

OSS_GLOBS = (
    "README.md",
    "SECURITY.md",
    "scripts/run_universal_root_*.py",
    "scripts/build_universal_root_*.py",
    "scripts/check_universal_root_*.py",
    "scripts/refresh_universal_root_*.py",
    "scripts/universal_root_*.py",
    "scripts/run_logos_graphrag_phase15*.py",
    "scripts/run_logos_graphrag_phase16*.py",
    "scripts/run_logos_graphrag_phase17*.py",
    "scripts/run_universal_root_oss_cursor_smoke_v1.py",
    "scripts/check_hardcoded_workspace_paths_v1.py",
    "scripts/normalize_workspace_paths_v1.py",
    "scripts/check_mkm_solo_oss_release_readiness_v1.py",
    "tests/test_universal_root_*.py",
    "docs/final/artifacts/UNIVERSAL_ROOT_*",
    "docs/final/artifacts/mkm_solo_oss_release_policy_v1_latest.json",
    "docs/final/artifacts/logos_neuro_symbolic_b2b_*",
    "docs/final/schemas/universal_root_*",
    "docs/final/artifacts/logos_neuro_symbolic_b2b_public_one_pager_ko_v1.md",
    "docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md",
    "docs/final/artifacts/mkm_universal_root_public_export_manifest_v1.json",
    "docs/final/artifacts/mkm_universal_root_readme_hero_en_v1.md",
    "scripts/build_mkm_universal_root_public_export_bundle_v1.py",
)

TEXT_SUFFIXES = {
    ".py",
    ".ps1",
    ".md",
    ".json",
    ".yaml",
    ".yml",
    ".txt",
    ".toml",
    ".sh",
    ".schema.json",
}


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _should_skip_rel(rel: str) -> bool:
    rel_norm = rel.replace("\\", "/")
    return any(rel_norm.startswith(p) for p in SKIP_REL_PREFIXES)


def _oss_files() -> list[Path]:
    found: set[Path] = set()
    for pattern in OSS_GLOBS:
        for path in ROOT.glob(pattern):
            if path.is_file():
                found.add(path.resolve())
    return sorted(found, key=_rel)


def _all_files() -> list[Path]:
    out: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        rel = _rel(path)
        if _should_skip_rel(rel):
            continue
        if any(part in SKIP_DIR_NAMES for part in path.parts):
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES and path.suffix not in TEXT_SUFFIXES:
            continue
        out.append(path)
    return out


def _is_false_positive(line: str) -> bool:
    if "re.compile" in line:
        return True
    if "no C:\\workspace" in line or "no C:/workspace" in line:
        return True
    return False


def _scan_file(path: Path) -> list[dict[str, Any]]:
    rel = _rel(path)
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    hits: list[dict[str, Any]] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        if _is_false_positive(line):
            continue
        for label, pat in PATTERNS:
            if pat.search(line):
                hits.append(
                    {
                        "file": rel,
                        "line": line_no,
                        "pattern": label,
                        "snippet": line.strip()[:200],
                        "tier": "A" if rel == "README.md" else "B",
                        "suggested_fix": "Use repo root relative paths or MKM_WORKSPACE_ROOT env",
                    }
                )
                break
    return hits


def run_audit(scope: str) -> dict[str, Any]:
    files = _oss_files() if scope == "oss" else _all_files()
    hits: list[dict[str, Any]] = []
    for path in files:
        hits.extend(_scan_file(path))
    by_file: dict[str, int] = {}
    for h in hits:
        by_file[h["file"]] = by_file.get(h["file"], 0) + 1
    return {
        "schema": "hardcoded_workspace_paths_audit_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "scope": scope,
        "files_scanned": len(files),
        "hit_count": len(hits),
        "files_with_hits": len(by_file),
        "ok": len(hits) == 0,
        "hits": hits,
        "by_file": by_file,
        "reproduce": f"py scripts/check_hardcoded_workspace_paths_v1.py --scope {scope} --strict",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scope", choices=("oss", "all"), default="oss")
    ap.add_argument("--strict", action="store_true", help="Exit 1 when hits > 0")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    doc = run_audit(args.scope)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    summary = {
        "ok": doc["ok"],
        "scope": doc["scope"],
        "hit_count": doc["hit_count"],
        "files_with_hits": doc["files_with_hits"],
        "out": str(args.out),
    }
    print(json.dumps(summary, ensure_ascii=False))
    if args.strict and not doc["ok"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
