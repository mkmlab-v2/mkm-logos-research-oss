#!/usr/bin/env python3
"""Thin llm_wiki / OKF frontmatter lint (validation only; no auto-classify).

  py scripts/check_llm_wiki_lint_v1.py
  py scripts/check_llm_wiki_lint_v1.py --strict
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
WIKI_ROOT = ROOT / "memory" / "obsidian_vault" / "llm_wiki"
OKF_ROOT = ROOT / "docs" / "final" / "artifacts" / "okf_bundles"
OUT = ROOT / "docs" / "final" / "artifacts" / "llm_wiki_lint_v1_latest.json"

CONTENT_TYPES = frozenset({"source_summary", "entity", "concept", "synthesis"})
WIKI_SCHEMAS = frozenset({"llm_wiki_wiki_v1", "llm_wiki_raw_v1", "okf_concept_v1"})
SCALAR_RE = re.compile(r"^([A-Za-z0-9_]+):\s*(.*)$")


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _parse_frontmatter(text: str) -> dict[str, Any] | None:
    """Parse simple YAML frontmatter; return None if no --- block."""
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    fm_raw = parts[1]
    fields: dict[str, Any] = {}
    current_list_key: str | None = None
    for line in fm_raw.splitlines():
        if not line.strip():
            continue
        if line.startswith("  - ") and current_list_key:
            fields.setdefault(current_list_key, []).append(line[4:].strip().strip("\"'"))
            continue
        m = SCALAR_RE.match(line)
        if not m:
            current_list_key = None
            continue
        key, val = m.group(1), m.group(2).strip()
        if val == "" or val == "[]":
            fields[key] = [] if val == "[]" else []
            current_list_key = key if val == "" else None
            continue
        current_list_key = None
        if (val.startswith('"') and val.endswith('"')) or (
            val.startswith("'") and val.endswith("'")
        ):
            val = val[1:-1]
        fields[key] = val
    return fields


def _iter_md(roots: list[Path]) -> list[Path]:
    out: list[Path] = []
    for root in roots:
        if not root.is_dir():
            continue
        out.extend(sorted(p for p in root.rglob("*.md") if p.is_file()))
    return out


def lint_file(path: Path, *, strict: bool) -> dict[str, Any]:
    rel = _rel(path)
    text = path.read_text(encoding="utf-8", errors="replace")
    fm = _parse_frontmatter(text)
    row: dict[str, Any] = {"path": rel, "ok": True, "errors": [], "warnings": []}

    if fm is None:
        row["status"] = "skipped_legacy_no_yaml"
        row["warnings"].append("no_yaml_frontmatter")
        return row

    schema = str(fm.get("schema") or "").strip()
    for key in ("schema", "type", "title"):
        if not str(fm.get(key) or "").strip():
            row["errors"].append(f"missing:{key}")

    ts = str(fm.get("timestamp") or fm.get("generated_at_utc") or "").strip()
    if not ts:
        row["errors"].append("missing:timestamp_or_generated_at_utc")

    if schema and schema not in WIKI_SCHEMAS:
        row["warnings"].append(f"unknown_schema:{schema}")

    ct = str(fm.get("content_type") or "").strip()
    if not ct:
        msg = "missing:content_type"
        if schema == "llm_wiki_wiki_v1" or strict:
            row["errors"].append(msg)
        else:
            row["warnings"].append(msg)
    elif ct not in CONTENT_TYPES:
        row["errors"].append(f"bad_content_type:{ct}")

    if schema == "llm_wiki_wiki_v1":
        if not str(fm.get("grade") or "").strip():
            row["errors"].append("missing:grade")
        if not str(fm.get("track") or "").strip():
            row["errors"].append("missing:track")

    # Soft reminder only — no PHI classifier.
    if "/llm_wiki/raw/" in rel.replace("\\", "/"):
        row["warnings"].append("raw_path_no_bulk_diary_phi_family")

    row["ok"] = not row["errors"]
    row["status"] = "ok" if row["ok"] else "fail"
    row["schema"] = schema or None
    row["content_type"] = ct or None
    return row


def run_lint(*, strict: bool) -> dict[str, Any]:
    roots = [WIKI_ROOT / "wiki", WIKI_ROOT / "raw", OKF_ROOT]
    present = [r for r in roots if r.is_dir()]
    files = _iter_md(present)

    if not present:
        return {
            "schema": "llm_wiki_lint_v1",
            "generated_at_utc": _utc(),
            "ok": True,
            "strict": strict,
            "skipped_empty": True,
            "roots_checked": [_rel(r) for r in roots],
            "files_scanned": 0,
            "error_count": 0,
            "warning_count": 0,
            "files": [],
            "reminder": "raw/ path: no bulk diary/PHI/family dumps",
            "reproducible_command": "py scripts/check_llm_wiki_lint_v1.py",
        }

    rows = [lint_file(p, strict=strict) for p in files]
    errors = [e for r in rows for e in r["errors"]]
    warnings = [w for r in rows for w in r["warnings"]]
    return {
        "schema": "llm_wiki_lint_v1",
        "generated_at_utc": _utc(),
        "ok": len(errors) == 0,
        "strict": strict,
        "skipped_empty": False,
        "roots_checked": [_rel(r) for r in present],
        "files_scanned": len(rows),
        "yaml_pages": sum(1 for r in rows if r.get("status") != "skipped_legacy_no_yaml"),
        "skipped_legacy_no_yaml": sum(
            1 for r in rows if r.get("status") == "skipped_legacy_no_yaml"
        ),
        "error_count": len(errors),
        "warning_count": len(warnings),
        "files": rows,
        "reminder": "raw/ path: no bulk diary/PHI/family dumps; no auto-classification",
        "reproducible_command": (
            "py scripts/check_llm_wiki_lint_v1.py --strict"
            if strict
            else "py scripts/check_llm_wiki_lint_v1.py"
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--strict",
        action="store_true",
        help="Fail on missing content_type for OKF pages too",
    )
    ap.add_argument(
        "--stdout-only",
        action="store_true",
        help="Do not write latest JSON artifact",
    )
    args = ap.parse_args()
    report = run_lint(strict=bool(args.strict))
    if not args.stdout_only:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        report["artifact"] = _rel(OUT)
    print(json.dumps({"ok": report["ok"], "error_count": report["error_count"], "artifact": report.get("artifact")}, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
