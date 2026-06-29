#!/usr/bin/env python3
"""Prune IJEOMA_BTRACK NL notebook: __pN split duplicates + stale image_picker uploads."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NB = "e6c1f050-40ef-49f0-8b2c-c509b8570cf4"
OUT = ROOT / "reports/notebooklm_ijoeoma_source_prune_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def list_sources(notebook_id: str) -> list[dict[str, Any]]:
    r = subprocess.run(
        ["nlm", "source", "list", notebook_id],
        capture_output=True,
        text=True,
        encoding="utf-8-sig",
        check=False,
    )
    if r.returncode != 0 or not r.stdout.strip():
        raise RuntimeError(f"nlm source list failed: {(r.stderr or r.stdout)[:300]}")
    parsed = json.loads(r.stdout)
    return parsed if isinstance(parsed, list) else []


def select_prune_ids(sources: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    titles = {str(x.get("title", "")) for x in sources}
    delete: list[dict[str, Any]] = []
    stats = {"__pN_duplicate": 0, "image_picker": 0}

    for row in sources:
        title = str(row.get("title", ""))
        sid = row.get("id")
        if not sid:
            continue
        m = re.search(r"__p(\d+)$", title)
        if m:
            base = title[: m.start()]
            if base in titles:
                delete.append(row)
                stats["__pN_duplicate"] += 1
            continue
        if "image_picker" in title or title.lower().endswith((".jpg", ".jpeg")):
            delete.append(row)
            stats["image_picker"] += 1

    return delete, stats


def delete_sources(source_ids: list[str], *, dry_run: bool) -> dict[str, Any]:
    if not source_ids:
        return {"deleted": 0, "batches": 0}
    if dry_run:
        return {"deleted": len(source_ids), "batches": 0, "dry_run": True}
    deleted = 0
    batches = 0
    batch_size = 40
    for i in range(0, len(source_ids), batch_size):
        batch = source_ids[i : i + batch_size]
        r = subprocess.run(
            ["nlm", "source", "delete", *batch, "--confirm"],
            capture_output=True,
            text=True,
            check=False,
        )
        batches += 1
        if r.returncode != 0:
            return {
                "deleted": deleted,
                "batches": batches,
                "ok": False,
                "error": (r.stderr or r.stdout)[-400:],
            }
        deleted += len(batch)
    return {"deleted": deleted, "batches": batches, "ok": True}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--notebook-id", default=DEFAULT_NB)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    before = list_sources(args.notebook_id)
    to_delete, stats = select_prune_ids(before)
    ids = [str(x["id"]) for x in to_delete]
    del_result = delete_sources(ids, dry_run=args.dry_run)
    after_count = len(before) - del_result.get("deleted", 0) if args.dry_run else None
    if not args.dry_run:
        after_count = len(list_sources(args.notebook_id))

    report = {
        "schema": "notebooklm_ijoeoma_source_prune_v1",
        "generated_at_utc": _utc(),
        "notebook_id": args.notebook_id,
        "dry_run": args.dry_run,
        "before_count": len(before),
        "selected_for_delete": len(ids),
        "selection_stats": stats,
        "delete_result": del_result,
        "after_count": after_count,
        "reproduce": [
            "py scripts/prune_notebooklm_ijoeoma_duplicate_sources_v1.py",
            "py scripts/prune_notebooklm_ijoeoma_duplicate_sources_v1.py --dry-run",
        ],
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": del_result.get("ok", True), "before": len(before), "deleted": del_result.get("deleted"), "after": after_count, "out": str(OUT)}, ensure_ascii=False))
    return 0 if del_result.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
