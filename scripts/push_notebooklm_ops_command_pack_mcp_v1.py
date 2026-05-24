#!/usr/bin/env python3
"""Push ops command sync pack to NotebookLM via stdio MCP (avoid if Cursor MCP active)."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "reports" / "notebooklm_ops_command_sync_pack_v1"
NOTEBOOKLM_JS = Path(
    os.environ.get(
        "NOTEBOOKLM_MCP_INDEX",
        r"C:/Users/PRO/AppData/Roaming/npm/node_modules/notebooklm-mcp/dist/index.js",
    )
)


def _server_params() -> StdioServerParameters:
    env = {
        "NOTEBOOKLM_PROFILE": os.environ.get("NOTEBOOKLM_PROFILE", "full"),
        "HEADLESS": os.environ.get("HEADLESS", "false"),
        "STEALTH_ENABLED": os.environ.get("STEALTH_ENABLED", "false"),
    }
    return StdioServerParameters(command="node", args=[str(NOTEBOOKLM_JS)], env=env)


def _parse_result(tool_result) -> dict:
    row = {"success": False, "sourceCountAfter": None, "error": None}
    if tool_result.isError:
        row["error"] = str(tool_result.content)
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


async def push_pack(notebook_url: str, skip_titles: set[str]) -> list[dict]:
    index = json.loads((PACK / "index.json").read_text(encoding="utf-8"))
    files = [f for f in index.get("files", []) if isinstance(f, str) and f not in skip_titles]
    rows: list[dict] = []
    async with stdio_client(_server_params()) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            session_id = ""
            for name in files:
                path = PACK / name
                if not path.is_file():
                    rows.append({"title": name, "success": False, "error": "missing"})
                    continue
                content = path.read_text(encoding="utf-8", errors="replace")
                args = {
                    "type": "text",
                    "title": name,
                    "content": content,
                    "notebook_url": notebook_url,
                }
                if session_id:
                    args["session_id"] = session_id
                row = {"title": name, "success": False}
                try:
                    result = await session.call_tool("add_source", args)
                    parsed = _parse_result(result)
                    row.update(parsed)
                except Exception as exc:  # noqa: BLE001
                    row["error"] = str(exc)
                rows.append(row)
                print(json.dumps(row, ensure_ascii=False), flush=True)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--notebook-url",
        default="https://notebooklm.google.com/notebook/9bc26140-70c4-47d0-b9ea-bd3a394916a9",
    )
    ap.add_argument("--skip", default="00_ops_command_handoff_snippet.md", help="comma names already pushed")
    ap.add_argument("--out", default=str(ROOT / "reports/notebooklm_ops_command_push_latest.json"))
    args = ap.parse_args()
    skip = {x.strip() for x in args.skip.split(",") if x.strip()}
    rows = asyncio.run(push_pack(args.notebook_url, skip))
    Path(args.out).write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if all(r.get("success") for r in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
