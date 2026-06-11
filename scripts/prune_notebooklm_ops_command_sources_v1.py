#!/usr/bin/env python3
"""Prune 00_OPS 지휘부 NL notebook to slim-pack keep set (+ optional extras).

Keeps sources whose base title (strip __pN chunks, sync suffix) matches the ops
command sync pack + anchor map + Gem ops prompt. Deletes orphans via nlm CLI.

SSOT pack: scripts/build_notebooklm_ops_command_sync_pack_v1.py
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NB_DEFAULT = "9bc26140-70c4-47d0-b9ea-bd3a394916a9"
OUT_DEFAULT = ROOT / "reports" / "notebooklm_ops_prune_result_v1_latest.json"

# Lens-pack NL titles (OPS_COMMAND_ANCHOR) — primary keep set (~5).
LENS_PACK_KEEP_TITLES = {
    "docs__NotebookLM_sources_manifest.md",
    "docs__final__CURRENT_OPS_SNAPSHOT.md",
    "docs__final__CENTRAL_AGENT_MEMORY_V1.md",
    "docs__final__P0_COMMERCIALIZATION_TRACKER.md",
    "docs__final__RESEARCH_HISTORY_V1.md",
}

KEEP_BASE_TITLES = set(LENS_PACK_KEEP_TITLES)

# NL KO UI labels MCP text paste as this; kept unless --prune-ko-paste-titles.
NEVER_DELETE_TITLES = {"붙여넣은 텍스트"}
KO_PASTE_TITLE = "붙여넣은 텍스트"


def base_title(raw: str) -> str:
    t = (raw or "").strip()
    if "__p" in t:
        t = t.split("__p", 1)[0]
    t = re.sub(r"\s*\(sync\s+[^)]+\)\s*$", "", t, flags=re.I)
    return t.strip()


def fetch_sources(notebook_id: str) -> list[dict]:
    raw = subprocess.check_output(
        ["nlm", "notebook", "get", notebook_id, "--json"],
        text=True,
        encoding="utf-8-sig",
    )
    data = json.loads(raw)
    val = data.get("value", data)
    return list(val.get("sources") or [])


def delete_source(source_id: str) -> bool:
    r = subprocess.run(
        ["nlm", "source", "delete", source_id, "--confirm"],
        capture_output=True,
        text=True,
    )
    return r.returncode == 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--notebook-id", default=NB_DEFAULT)
    ap.add_argument("--what-if", action="store_true")
    ap.add_argument(
        "--prune-ko-paste-titles",
        action="store_true",
        help="Delete sources titled '붙여넣은 텍스트' (legacy MCP text paste); nlm push preferred.",
    )
    ap.add_argument("--out", default=str(OUT_DEFAULT))
    args = ap.parse_args()

    sources = fetch_sources(args.notebook_id)
    to_delete: list[dict] = []
    kept: list[dict] = []
    for s in sources:
        sid = s.get("id", "")
        title = s.get("title", "")
        base = base_title(title)
        row = {"id": sid, "title": title, "base_title": base}
        if title in KEEP_BASE_TITLES or base in KEEP_BASE_TITLES:
            kept.append(row)
        elif args.prune_ko_paste_titles and (title == KO_PASTE_TITLE or base == KO_PASTE_TITLE):
            to_delete.append({**row, "note": "ko_paste_title_cleanup"})
        elif title in NEVER_DELETE_TITLES or base in NEVER_DELETE_TITLES:
            kept.append({**row, "note": "nl_paste_title_preserved"})
        else:
            to_delete.append(row)

    doc = {
        "schema": "notebooklm_ops_prune_result_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "notebook_id": args.notebook_id,
        "keep_base_titles": sorted(KEEP_BASE_TITLES),
        "sources_before": len(sources),
        "keep_count": len(kept),
        "delete_count": len(to_delete),
        "delete": to_delete,
        "kept_base_summary": sorted({k["base_title"] for k in kept}),
        "missing_keep_bases": sorted(KEEP_BASE_TITLES - {k["base_title"] for k in kept}),
    }

    if args.what_if:
        Path(args.out).write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"what_if": True, "delete_count": len(to_delete), "out": args.out}, ensure_ascii=False))
        return 0

    ok = fail = 0
    for row in to_delete:
        if delete_source(row["id"]):
            ok += 1
        else:
            fail += 1

    sources_after = fetch_sources(args.notebook_id)
    doc["deleted_ok"] = ok
    doc["deleted_fail"] = fail
    doc["sources_after"] = len(sources_after)
    Path(args.out).write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"deleted_ok": ok, "deleted_fail": fail, "sources_after": len(sources_after), "out": args.out}, ensure_ascii=False))
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
