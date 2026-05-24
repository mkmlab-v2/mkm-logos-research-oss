#!/usr/bin/env python3
"""Add nl_mcp_payload sources via stdio MCP. Run only when Cursor NotebookLM MCP is OFF."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

PILOT = Path(__file__).resolve().parents[1] / "reports" / "constitution" / "btrack_pilot"
NOTEBOOKLM_JS = Path(
    os.environ.get(
        "NOTEBOOKLM_MCP_INDEX",
        r"C:/Users/PRO/AppData/Roaming/npm/node_modules/notebooklm-mcp/dist/index.js",
    )
)
NOTEBOOK_ID = "mkm-core-intelligence-fact-foc"
OUT_DEFAULT = PILOT / "nl_add_results_cursor_batch_latest.json"


def _server_params() -> StdioServerParameters:
    env = {
        "NOTEBOOKLM_PROFILE": os.environ.get("NOTEBOOKLM_PROFILE", "full"),
        "HEADLESS": os.environ.get("HEADLESS", "false"),
        "MKM_NOTEBOOKLM_MCP_PINNED_VERSION": os.environ.get(
            "MKM_NOTEBOOKLM_MCP_PINNED_VERSION", "2.0.0"
        ),
        "STEALTH_ENABLED": os.environ.get("STEALTH_ENABLED", "false"),
    }
    return StdioServerParameters(command="node", args=[str(NOTEBOOKLM_JS)], env=env)


def _load_args(index: int, session_id: str) -> dict:
    data = json.loads((PILOT / f"nl_mcp_payload_{index}.json").read_text(encoding="utf-8"))
    out = {
        "type": "text",
        "title": data["title"],
        "content": data["content"],
        "notebook_id": NOTEBOOK_ID,
    }
    if session_id:
        out["session_id"] = session_id
    return out


def _parse_result(tool_result) -> dict:
    row = {"success": False, "sourceCountBefore": None, "sourceCountAfter": None, "error": None}
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
            row["sourceCountBefore"] = inner.get("sourceCountBefore")
            row["sourceCountAfter"] = inner.get("sourceCountAfter")
            if inner.get("error"):
                row["error"] = inner["error"]
            return row
    row["error"] = "unparsed tool result"
    return row


async def run_indices(indices: list[int], session_id: str) -> list[dict]:
    rows: list[dict] = []
    async with stdio_client(_server_params()) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            health = await session.call_tool("get_health", {})
            for block in health.content or []:
                t = getattr(block, "text", "") or ""
                if t.strip().startswith("{"):
                    hj = json.loads(t)
                    auth = (hj.get("data") or hj).get("authenticated")
                    if auth is not True:
                        print("WARN: authenticated != true", file=sys.stderr)
                    break
            for i in indices:
                title = _load_args(i, session_id)["title"]
                row = {
                    "index": i,
                    "title": title,
                    "success": False,
                    "sourceCountAfter": None,
                    "error": None,
                }
                try:
                    result = await session.call_tool("add_source", _load_args(i, session_id))
                    parsed = _parse_result(result)
                    row.update(parsed)
                except Exception as exc:  # noqa: BLE001
                    row["error"] = str(exc)
                rows.append(row)
                print(json.dumps(row, ensure_ascii=False), flush=True)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--indices", default="0,1,2,3,4,5,6,7")
    ap.add_argument("--session-id", default="00e4c8db")
    ap.add_argument("--out", default=str(OUT_DEFAULT))
    args = ap.parse_args()
    indices = [int(x.strip()) for x in args.indices.split(",") if x.strip()]
    rows = asyncio.run(run_indices(indices, args.session_id))
    Path(args.out).write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if all(r.get("success") for r in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
