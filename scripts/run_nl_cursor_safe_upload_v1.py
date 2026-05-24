#!/usr/bin/env python3
"""Upload nl_cursor_upload_queue via stdio MCP — run only when Cursor MCP is OFF."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parent.parent
QUEUE = ROOT / "reports/constitution/btrack_pilot/nl_cursor_upload_queue_v1.json"
OUT = ROOT / "reports/constitution/btrack_pilot/comp_nl_auto_upload_result_v1.json"
CHUNK = 8000

NOTEBOOKLM_JS = Path(
    os.environ.get(
        "NOTEBOOKLM_MCP_INDEX",
        r"C:/Users/PRO/AppData/Roaming/npm/node_modules/notebooklm-mcp/dist/index.js",
    )
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _node_count() -> int:
    import subprocess

    try:
        out = subprocess.check_output(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "(Get-CimInstance Win32_Process -Filter \"name='node.exe'\" | "
                "Where-Object { $_.CommandLine -match 'notebooklm-mcp' }).Count",
            ],
            text=True,
            timeout=20,
        )
        return int(out.strip() or "0")
    except Exception:
        return 0


def _server_params() -> StdioServerParameters:
    return StdioServerParameters(
        command="node",
        args=[str(NOTEBOOKLM_JS)],
        env={
            "NOTEBOOKLM_PROFILE": os.environ.get("NOTEBOOKLM_PROFILE", "full"),
            "HEADLESS": os.environ.get("HEADLESS", "false"),
            "STEALTH_ENABLED": "false",
        },
    )


def _parse_result(tool_result) -> dict:
    if tool_result.isError:
        return {"success": False, "error": str(tool_result.content)}
    for block in tool_result.content or []:
        text = getattr(block, "text", "") or ""
        if not text.strip().startswith("{"):
            continue
        payload = json.loads(text)
        inner = payload.get("data", payload).get("result", payload.get("data", payload))
        if isinstance(inner, dict):
            return {
                "success": bool(inner.get("success")),
                "sourceCountAfter": inner.get("sourceCountAfter"),
                "error": inner.get("error"),
            }
    return {"success": False, "error": "unparsed"}


async def _upload(session: ClientSession, item: dict) -> list[dict]:
    rows: list[dict] = []
    body = item["content"]
    parts = [body[i : i + CHUNK] for i in range(0, len(body), CHUNK)] or [""]
    for i, part in enumerate(parts):
        title = item["title"] if len(parts) == 1 else f"{item['title']}__p{i}"
        row = {"title": title, "notebook_id": item["notebook_id"], "chars": len(part)}
        try:
            r = await session.call_tool(
                "add_source",
                {
                    "type": "text",
                    "content": part,
                    "title": title[:120],
                    "notebook_id": item["notebook_id"],
                },
            )
            row.update(_parse_result(r))
        except Exception as exc:  # noqa: BLE001
            row["success"] = False
            row["error"] = str(exc)
        rows.append(row)
        print(json.dumps(row, ensure_ascii=False), flush=True)
    return rows


async def main_async() -> dict:
    items = json.loads(QUEUE.read_text(encoding="utf-8"))
    all_rows: list[dict] = []
    async with stdio_client(_server_params()) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            h = await session.call_tool("get_health", {})
            auth = False
            for block in h.content or []:
                t = getattr(block, "text", "") or ""
                if t.strip().startswith("{"):
                    auth = json.loads(t).get("data", {}).get("authenticated") is True
            if not auth:
                return {"error": "authenticated_false", "rows": []}
            for item in items:
                all_rows.extend(await _upload(session, item))
    ok = sum(1 for r in all_rows if r.get("success"))
    fail = sum(1 for r in all_rows if not r.get("success"))
    return {
        "schema": "comp_nl_auto_upload_result_v1",
        "generated_at_utc": _utc(),
        "commander_approved": True,
        "method": "stdio_mcp_safe_queue",
        "ok": ok,
        "fail": fail,
        "success": fail == 0 and ok > 0,
        "rows": all_rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--allow-with-cursor-mcp",
        action="store_true",
        help="Skip check for existing notebooklm-mcp node (not recommended).",
    )
    args = parser.parse_args()
    n = _node_count()
    if n >= 1 and not args.allow_with_cursor_mcp:
        print(
            json.dumps(
                {
                    "error": "cursor_mcp_active",
                    "node_count": n,
                    "hint": "Turn OFF notebooklm in Cursor MCP, Reload Window, then re-run this script.",
                },
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 3
    doc = asyncio.run(main_async())
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": OUT.name, "ok": doc.get("ok"), "fail": doc.get("fail")}, ensure_ascii=False))
    return 0 if doc.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
