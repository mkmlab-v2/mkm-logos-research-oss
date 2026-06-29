#!/usr/bin/env python3
"""Incremental patch MERGED/LIT_REVIEW SSOT when new Tier-0 raw drops arrive."""

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

from scripts.build_mkm_raw_drop_delta_v1 import (  # noqa: E402
    build_raw_drop_delta,
    file_sha256,
)
from scripts.check_research_lit_review_citation_lock_v1 import (  # noqa: E402
    extract_arxiv_ids,
    fetch_arxiv_metadata_batch,
)

DEFAULT_RAW_DIR = ROOT / "docs" / "research" / "raw"
DEFAULT_MANIFEST_DIR = ROOT / "docs" / "final" / "artifacts"
PART_VII_MARKER = "## Part VII"
INCREMENTAL_SECTION = "## Part VI.G — Incremental raw drop"
INPUTS_TABLE_MARKER = "| Tier | File | Role |"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _utc_date() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _posix_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def manifest_path(*, topic_slug: str, manifest_dir: Path = DEFAULT_MANIFEST_DIR) -> Path:
    return manifest_dir / f"{topic_slug}_remerge_manifest_latest.json"


def load_manifest(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {
            "schema": "mkm_merged_lit_review_remerge_manifest_v1",
            "version": "1.0.0",
            "raw_files": [],
            "merge_mode": "incremental_patch_full_gate",
        }
    doc = json.loads(path.read_text(encoding="utf-8"))
    if doc.get("schema") != "mkm_merged_lit_review_remerge_manifest_v1":
        raise ValueError(f"unexpected manifest schema in {path}")
    return doc


def save_manifest(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def list_raw_markdown(raw_dir: Path) -> list[Path]:
    if not raw_dir.is_dir():
        return []
    out: list[Path] = []
    for path in sorted(raw_dir.glob("*.md")):
        if not path.is_file():
            continue
        name = path.name.lower()
        if "_explore_" in name:
            continue
        out.append(path.resolve())
    return out


def manifest_index(manifest: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for row in manifest.get("raw_files") or []:
        if not isinstance(row, dict):
            continue
        path = str(row.get("path") or "")
        sha = str(row.get("sha256") or "")
        if path and sha:
            out[path] = sha
    return out


def detect_changed_raw_files(
    *,
    raw_files: list[Path],
    manifest: dict[str, Any],
) -> list[Path]:
    indexed = manifest_index(manifest)
    changed: list[Path] = []
    for path in raw_files:
        rel = _posix_path(path)
        sha = file_sha256(path)
        if indexed.get(rel) != sha:
            changed.append(path)
    return changed


def _next_catalog_row_number(text: str) -> int:
    numbers = [int(m.group(1)) for m in re.finditer(r"^\|\s*(\d+)\s*\|", text, re.MULTILINE)]
    return max(numbers) + 1 if numbers else 1


def _title_for_arxiv(aid: str, *, offline: bool) -> str:
    if offline:
        return aid
    meta = fetch_arxiv_metadata_batch([aid])
    rec = meta.get(aid) or {}
    title = rec.get("title")
    if isinstance(title, str) and title.strip():
        return title.strip().replace("|", "/")
    return aid


def _ensure_inputs_row(text: str, *, raw_rel: str, date: str) -> str:
    row = f"| **0x** | `{raw_rel}` | Incremental raw drop ({date}) |"
    if raw_rel in text:
        return text
    if INPUTS_TABLE_MARKER not in text:
        header = (
            "**Inputs:**\n\n"
            "| Tier | File | Role |\n"
            "|------|------|------|\n"
            f"{row}\n\n"
        )
        return header + text
    lines = text.splitlines()
    out: list[str] = []
    inserted = False
    for line in lines:
        out.append(line)
        if not inserted and line.strip() == "|------|------|------|":
            out.append(row)
            inserted = True
    return "\n".join(out) + ("\n" if text.endswith("\n") else "")


def _update_stats_line(text: str) -> str:
    ids = extract_arxiv_ids(text)
    count = len(ids)
    pattern = re.compile(r"\*\*Stats:\*\*.*", re.MULTILINE)
    replacement = f"**Stats:** **~{count} papers/systems** (incremental re-merge {_utc_date()})"
    if pattern.search(text):
        return pattern.sub(replacement, text, count=1)
    return text


def _build_incremental_section(
    *,
    date: str,
    deltas: list[dict[str, Any]],
    start_row: int,
    offline: bool,
) -> tuple[str, int]:
    lines = [
        "",
        INCREMENTAL_SECTION + f" ({date})",
        "",
        "| # | ID | Title | Source raw | MKM tag |",
        "|---|-----|-------|------------|---------|",
    ]
    row_num = start_row
    for delta in deltas:
        source = str(delta.get("source_path") or "")
        new_ids = delta.get("new_arxiv_ids") or delta.get("arxiv_ids") or []
        for aid in new_ids:
            title = _title_for_arxiv(str(aid), offline=offline)
            lines.append(f"| {row_num} | {aid} | {title} | `{source}` | raw_drop `[HYPO]` |")
            row_num += 1
    lines.append("")
    return "\n".join(lines), row_num


def _insert_incremental_section(text: str, section: str) -> str:
    if INCREMENTAL_SECTION in text:
        marker = INCREMENTAL_SECTION
        idx = text.find(marker)
        before = text[:idx].rstrip()
        after_idx = text.find(PART_VII_MARKER, idx)
        after = text[after_idx:] if after_idx != -1 else ""
        return before + "\n" + section.strip() + "\n\n" + after.lstrip()
    if PART_VII_MARKER in text:
        head, tail = text.split(PART_VII_MARKER, 1)
        return head.rstrip() + "\n" + section.strip() + "\n\n" + PART_VII_MARKER + tail
    return text.rstrip() + "\n" + section.strip() + "\n"


def _append_remerge_manifest_block(text: str, *, manifest_doc: dict[str, Any]) -> str:
    block = (
        "\n\n## Re-merge manifest (auto)\n\n"
        f"- last_remerge_utc: `{manifest_doc.get('last_remerge_utc')}`\n"
        f"- merge_mode: `{manifest_doc.get('merge_mode')}`\n"
        f"- raw_file_count: `{len(manifest_doc.get('raw_files') or [])}`\n"
    )
    marker = "## Re-merge manifest (auto)"
    if marker in text:
        head = text.split(marker, 1)[0].rstrip()
        return head + block
    return text.rstrip() + block


def apply_incremental_patch(
    *,
    merged_text: str,
    deltas: list[dict[str, Any]],
    offline: bool,
) -> str:
    text = merged_text
    date = _utc_date()
    for delta in deltas:
        text = _ensure_inputs_row(text, raw_rel=str(delta.get("source_path") or ""), date=date)
    start_row = _next_catalog_row_number(text)
    section, _ = _build_incremental_section(date=date, deltas=deltas, start_row=start_row, offline=offline)
    text = _insert_incremental_section(text, section)
    text = _update_stats_line(text)
    return text


def build_deltas_for_files(
    *,
    raw_files: list[Path],
    query: str,
    baseline_md: Path | None,
    use_ollama: bool,
) -> list[dict[str, Any]]:
    baseline_ids: set[str] = set()
    if baseline_md and baseline_md.is_file():
        baseline_ids = set(extract_arxiv_ids(baseline_md.read_text(encoding="utf-8", errors="replace")))
    out: list[dict[str, Any]] = []
    for path in raw_files:
        out.append(
            build_raw_drop_delta(
                source_path=path,
                query=query,
                baseline_arxiv_ids=baseline_ids,
                use_ollama=use_ollama,
            )
        )
        for aid in out[-1].get("arxiv_ids") or []:
            baseline_ids.add(str(aid))
    return out


def refresh_manifest_raw_files(
    *,
    manifest: dict[str, Any],
    raw_files: list[Path],
    merged_md: Path,
    topic_slug: str,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for path in raw_files:
        rel = _posix_path(path)
        rows.append(
            {
                "path": rel,
                "sha256": file_sha256(path),
                "ingested_at_utc": _utc_now(),
            }
        )
    manifest.update(
        {
            "schema": "mkm_merged_lit_review_remerge_manifest_v1",
            "version": "1.0.0",
            "topic_slug": topic_slug,
            "merged_md": _posix_path(merged_md),
            "raw_files": rows,
            "last_remerge_utc": _utc_now(),
            "merge_mode": "incremental_patch_full_gate",
            "research_only": True,
            "send_gate": "HOLD",
        }
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Incremental patch MERGED/LIT_REVIEW from raw drops")
    parser.add_argument("--merged", type=Path, required=True)
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--topic-slug", required=True)
    parser.add_argument("--query", default="research raw drop incremental")
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--use-ollama", action="store_true")
    parser.add_argument("--no-ollama", action="store_true")
    parser.add_argument("--force-all", action="store_true", help="Re-process every raw md even if manifest matches")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    merged_path = args.merged.resolve()
    if not merged_path.is_file():
        print(json.dumps({"ok": False, "error": f"missing merged: {merged_path}"}, ensure_ascii=False))
        return 2

    manifest_file = args.manifest.resolve() if args.manifest else manifest_path(topic_slug=args.topic_slug)
    manifest_exists = manifest_file.is_file()
    manifest = load_manifest(manifest_file)
    raw_files = list_raw_markdown(args.raw_dir.resolve())

    if not manifest_exists:
        manifest = refresh_manifest_raw_files(
            manifest=manifest,
            raw_files=raw_files,
            merged_md=merged_path,
            topic_slug=args.topic_slug,
        )
        if not args.dry_run:
            save_manifest(manifest_file, manifest)
        print(
            json.dumps(
                {
                    "ok": True,
                    "changed": False,
                    "bootstrapped": True,
                    "merged_md": _posix_path(merged_path),
                    "manifest_path": _posix_path(manifest_file),
                    "raw_file_count": len(raw_files),
                },
                ensure_ascii=False,
            )
        )
        return 0

    changed = raw_files if args.force_all else detect_changed_raw_files(raw_files=raw_files, manifest=manifest)
    if not changed:
        print(
            json.dumps(
                {
                    "ok": True,
                    "changed": False,
                    "merged_md": _posix_path(merged_path),
                    "manifest_path": _posix_path(manifest_file),
                },
                ensure_ascii=False,
            )
        )
        return 0

    use_ollama = bool(args.use_ollama and not args.no_ollama)
    deltas = build_deltas_for_files(
        raw_files=changed,
        query=args.query,
        baseline_md=merged_path,
        use_ollama=use_ollama,
    )
    merged_text = merged_path.read_text(encoding="utf-8", errors="replace")
    patched = apply_incremental_patch(merged_text=merged_text, deltas=deltas, offline=args.offline)
    manifest = refresh_manifest_raw_files(
        manifest=manifest,
        raw_files=raw_files,
        merged_md=merged_path,
        topic_slug=args.topic_slug,
    )
    patched = _append_remerge_manifest_block(patched, manifest_doc=manifest)

    if not args.dry_run:
        merged_path.write_text(patched, encoding="utf-8")
        save_manifest(manifest_file, manifest)

    new_ids = sorted({aid for d in deltas for aid in (d.get("new_arxiv_ids") or [])})
    changed_paths = [_posix_path(p) for p in changed]
    plane_votes: dict[str, int] = {}
    for delta in deltas:
        plane = str(delta.get("plane_hint") or "research_meta")
        plane_votes[plane] = plane_votes.get(plane, 0) + 1
    plane_hint = max(plane_votes, key=plane_votes.get) if plane_votes else "research_meta"
    print(
        json.dumps(
            {
                "ok": True,
                "changed": True,
                "dry_run": args.dry_run,
                "merged_md": _posix_path(merged_path),
                "manifest_path": _posix_path(manifest_file),
                "changed_raw_count": len(changed),
                "changed_raw_paths": changed_paths,
                "plane_hint": plane_hint,
                "new_arxiv_ids": new_ids,
                "new_arxiv_id_count": len(new_ids),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
