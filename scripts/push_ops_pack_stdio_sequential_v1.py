#!/usr/bin/env python3
"""Push ops pack to 00_OPS via stdio MCP — one file at a time (Cursor MCP chrome idle).

Usage:
  py scripts/push_ops_pack_stdio_sequential_v1.py
  py scripts/push_ops_pack_stdio_sequential_v1.py --only AGENTS.md,CENTRAL_AGENT_MEMORY_V1.md
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "reports" / "notebooklm_ops_command_sync_pack_v1"
OPS_URL = "https://notebooklm.google.com/notebook/9bc26140-70c4-47d0-b9ea-bd3a394916a9"
NOTEBOOKLM_JS = Path(
    os.environ.get(
        "NOTEBOOKLM_MCP_INDEX",
        r"C:/Users/PRO/AppData/Roaming/npm/node_modules/notebooklm-mcp/dist/index.js",
    )
)
CHUNK = 120_000
SKIP_TITLES: set[str] = set()
ALREADY = {
    "parallel_ops_run_2026-05-23_latest.json",
    "compression_track_a_headline_policy_v1_latest.json",
    "RESEARCH_HISTORY_V1.md",
}


def _server_params() -> StdioServerParameters:
    return StdioServerParameters(
        command="node",
        args=[str(NOTEBOOKLM_JS)],
        env={
            "NOTEBOOKLM_PROFILE": os.environ.get("NOTEBOOKLM_PROFILE", "full"),
            "HEADLESS": os.environ.get("HEADLESS", "false"),
            "STEALTH_ENABLED": os.environ.get("STEALTH_ENABLED", "false"),
        },
    )


def _parse_result(tool_result) -> dict:
    row = {"success": False, "sourceCountAfter": None, "error": None}
    if tool_result.isError:
        row["error"] = str(tool_result.content)[:500]
        return row
    for block in tool_result.content or []:
        text = getattr(block, "text", None)
        if not text:
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            continue
        inner = payload.get("data", payload)
        if isinstance(inner, dict) and "result" in inner:
            inner = inner["result"]
        if isinstance(inner, dict):
            row["success"] = bool(inner.get("success", payload.get("success")))
            row["sourceCountAfter"] = inner.get("sourceCountAfter")
            row["error"] = inner.get("error")
            return row
    row["error"] = "unparsed"
    return row


def _chunks(name: str, text: str) -> list[tuple[str, str]]:
    if len(text) <= CHUNK:
        return [(name, text)]
    parts = [text[i : i + CHUNK] for i in range(0, len(text), CHUNK)]
    return [(f"{name}__part{i+1}of{len(parts)}", p) for i, p in enumerate(parts)]


async def push_all(only: set[str] | None, pause_s: float) -> list[dict]:
    index = json.loads((PACK / "index.json").read_text(encoding="utf-8"))
    queue: list[tuple[str, str]] = []
    for name in index["files"]:
        if name in SKIP_TITLES or name in ALREADY:
            continue
        if only and name not in only:
            continue
        path = PACK / name
        if not path.is_file():
            continue
        queue.extend(_chunks(name, path.read_text(encoding="utf-8", errors="replace")))

    rows: list[dict] = []
    session_id = ""
    for title, content in queue:
        args = {
            "type": "text",
            "title": title,
            "content": content,
            "notebook_url": OPS_URL,
        }
        if session_id:
            args["session_id"] = session_id
        row = {"title": title, "success": False}
        async with stdio_client(_server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                try:
                    result = await session.call_tool("add_source", args)
                    parsed = _parse_result(result)
                    row.update(parsed)
                except Exception as exc:  # noqa: BLE001
                    row["error"] = str(exc)[:500]
        rows.append(row)
        print(json.dumps(row, ensure_ascii=False), flush=True)
        if pause_s > 0:
            time.sleep(pause_s)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="comma-separated basenames")
    ap.add_argument("--pause", type=float, default=3.0)
    ap.add_argument("--out", default=str(ROOT / "reports/notebooklm_ops_command_push_latest.json"))
    args = ap.parse_args()
    only = {x.strip() for x in args.only.split(",") if x.strip()} or None
    rows = asyncio.run(push_all(only, args.pause))
    Path(args.out).write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if rows and all(r.get("success") for r in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
