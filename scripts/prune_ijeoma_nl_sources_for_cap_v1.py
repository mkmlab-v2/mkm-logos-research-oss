#!/usr/bin/env python3
"""Prune low-priority IJEOMA NL sources to free slots for donguibogam completion (reproducible)."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UUID = "e6c1f050-40ef-49f0-8b2c-c509b8570cf4"
OUT = ROOT / "reports/constitution/btrack_pilot/ijeoma_nl_prune_for_cap_v1.json"
CAP = 300
BATCH = 8

# Disk SSOT remains; NL trim only. SASANG_CROSS_REF draft is large vs donguibogam vendor completion.
TRIM_TITLE_PREFIXES = (
    "SASANG_CROSS_REF",
    "tier0_",
    "km_classics_vendor_mirror_report",
    "hwp_com_export_report",
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sources() -> list[dict]:
    proc = subprocess.run(
        ["nlm", "notebook", "get", UUID, "--json"],
        capture_output=True,
        text=True,
        encoding="utf-8-sig",
        errors="replace",
        cwd=str(ROOT),
    )
    proc.check_returncode()
    payload = json.loads(proc.stdout)
    val = payload.get("value") or payload
    return list(val.get("sources") or [])


def _dedupe_candidates(src: list[dict]) -> list[dict]:
    """Keep one source per title (newest last in API order); delete older duplicates."""
    by_title: dict[str, list[dict]] = {}
    for s in src:
        title = s.get("title") or ""
        by_title.setdefault(title, []).append(s)
    out: list[dict] = []
    for title, items in by_title.items():
        if len(items) < 2:
            continue
        for s in items[:-1]:
            out.append({"id": s["id"], "title": title, "reason": "duplicate_title"})
    return out


def _trim_prefix_candidates(src: list[dict]) -> list[dict]:
    out: list[dict] = []
    for s in src:
        title = s.get("title") or ""
        if any(title.startswith(p) or p in title for p in TRIM_TITLE_PREFIXES):
            out.append({"id": s["id"], "title": title, "reason": "trim_prefix"})
    return out


def _merge_delete_candidates(*groups: list[dict]) -> list[dict]:
    seen: set[str] = set()
    merged: list[dict] = []
    for group in groups:
        for item in group:
            sid = item["id"]
            if sid in seen:
                continue
            seen.add(sid)
            merged.append(item)
    return merged


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dedupe-titles", action="store_true", help="Delete older duplicate titles (keep newest)")
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--what-if", action="store_true")
    args = parser.parse_args()

    src = _sources()
    pre = len(src)
    prefix_hits = _trim_prefix_candidates(src)
    dedupe_hits = _dedupe_candidates(src) if args.dedupe_titles else []
    to_delete = _merge_delete_candidates(prefix_hits, dedupe_hits)

    doc = {
        "schema": "ijeoma_nl_prune_for_cap_v1",
        "generated_at_utc": _utc(),
        "notebook_uuid": UUID,
        "pre_count": pre,
        "trim_candidates": len(to_delete),
        "trim_prefix_count": len(prefix_hits),
        "dedupe_count": len(dedupe_hits),
        "titles": [x["title"] for x in to_delete],
    }

    if args.what_if or not args.confirm:
        doc["mode"] = "what_if"
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(doc, ensure_ascii=False))
        return 0

    ids = [x["id"] for x in to_delete]
    deleted = 0
    failed: list[str] = []
    for i in range(0, len(ids), BATCH):
        chunk = ids[i : i + BATCH]
        proc = subprocess.run(
            ["nlm", "source", "delete", *chunk, "--confirm"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(ROOT),
        )
        if proc.returncode == 0:
            deleted += len(chunk)
        else:
            failed.extend(chunk)
        time.sleep(1)

    post = len(_sources())
    doc.update(
        {
            "mode": "confirm",
            "deleted": deleted,
            "failed_ids": failed,
            "post_count": post,
            "slots_for_donguibogam": max(0, CAP - post),
        }
    )
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(doc, ensure_ascii=False))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
