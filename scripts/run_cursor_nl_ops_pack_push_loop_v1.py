#!/usr/bin/env python3
"""Emit per-file MCP add_source payloads for Cursor agent (no stdio Chrome).

Writes one JSON per pack file under reports/notebooklm_ops_push_cursor_queue/.
Agent: read each *.payload.json and CallMcpTool add_source with arguments field.

Usage:
  py scripts/run_cursor_nl_ops_pack_push_loop_v1.py
  py scripts/run_cursor_nl_ops_pack_push_loop_v1.py --only AGENTS.md,P0_COMMERCIALIZATION_TRACKER.md
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "reports" / "notebooklm_ops_command_sync_pack_v1"
OUT = ROOT / "reports" / "notebooklm_ops_push_cursor_queue"
OPS_URL = "https://notebooklm.google.com/notebook/9bc26140-70c4-47d0-b9ea-bd3a394916a9"
CHUNK = 100_000
SKIP_DEFAULT = {
    "parallel_ops_run_2026-05-23_latest.json",
    "compression_track_a_headline_policy_v1_latest.json",
    "RESEARCH_HISTORY_V1.md",
}


def _safe(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", name)[:80]


def _chunk_titles(name: str, text: str) -> list[tuple[str, str]]:
    if len(text) <= CHUNK:
        return [(name, text)]
    parts = [text[i : i + CHUNK] for i in range(0, len(text), CHUNK)]
    return [(f"{name}__part{i+1}of{len(parts)}", p) for i, p in enumerate(parts)]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="comma basenames")
    ap.add_argument("--skip", default="", help="comma extra skip")
    ap.add_argument("--notebook-url", default=OPS_URL)
    args = ap.parse_args()
    index = json.loads((PACK / "index.json").read_text(encoding="utf-8"))
    files = index.get("files", [])
    if args.only.strip():
        want = {x.strip() for x in args.only.split(",") if x.strip()}
        files = [f for f in files if f in want]
    skip = set(SKIP_DEFAULT) | {x.strip() for x in args.skip.split(",") if x.strip()}
    OUT.mkdir(parents=True, exist_ok=True)
    manifest: list[dict] = []
    for name in files:
        if name in skip:
            manifest.append({"title": name, "skipped": True, "payload": None})
            continue
        path = PACK / name
        if not path.is_file():
            manifest.append({"title": name, "error": "missing", "payload": None})
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for title, chunk in _chunk_titles(name, text):
            payload = {
                "server": "project-0-workspace-notebooklm",
                "toolName": "add_source",
                "arguments": {
                    "type": "text",
                    "title": title,
                    "content": chunk,
                    "notebook_id": "00-ops-2026q2",
                    "notebook_url": args.notebook_url,
                },
            }
            out = OUT / f"{_safe(title)}.payload.json"
            out.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            manifest.append(
                {
                    "title": title,
                    "payload": str(out.relative_to(ROOT)).replace("\\", "/"),
                    "chars": len(chunk),
                }
            )
    (OUT / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"out": str(OUT), "items": len(manifest)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
