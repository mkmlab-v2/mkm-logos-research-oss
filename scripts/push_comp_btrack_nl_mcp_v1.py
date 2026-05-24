#!/usr/bin/env python3
"""Push COMPRESSION_BTRACK + IJEOMA_BTRACK packs via NotebookLM MCP add_source (text)."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parent.parent
PACK_ROOT = ROOT / "reports/notebooklm_lens_packs_v1"
OUT = ROOT / "reports/constitution/btrack_pilot/comp_nl_auto_upload_result_v1.json"
CHUNK_CHARS = 38_000
MAX_SINGLE = 480_000

NOTEBOOKLM_JS = Path(
    os.environ.get(
        "NOTEBOOKLM_MCP_INDEX",
        r"C:/Users/PRO/AppData/Roaming/npm/node_modules/notebooklm-mcp/dist/index.js",
    )
)

LENS_NOTEBOOK = {
    "COMPRESSION_BTRACK": "mkm-core-intelligence-fact-foc",
    "IJEOMA_BTRACK": "ai-b-mkm-abstract",
}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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


def _chunks(text: str) -> list[str]:
    if len(text) <= MAX_SINGLE:
        return [text]
    return [text[i : i + CHUNK_CHARS] for i in range(0, len(text), CHUNK_CHARS)]


def _parse_result(tool_result) -> dict:
    out: dict = {"success": False, "error": None}
    if tool_result.isError:
        out["error"] = str(tool_result.content)
        return out
    for block in tool_result.content or []:
        text = getattr(block, "text", None) or ""
        if not text.strip().startswith("{"):
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            continue
        inner = payload.get("data", payload)
        if isinstance(inner, dict) and "result" in inner:
            inner = inner["result"]
        if isinstance(inner, dict):
            out["success"] = bool(inner.get("success", payload.get("success")))
            if inner.get("error"):
                out["error"] = inner["error"]
            return out
    out["error"] = "unparsed"
    return out


PRIORITY_FILENAMES = (
    "reports__constitution__btrack_pilot__comp_cross_chat_achievement_index_v1.json",
    "reports__constitution__btrack_pilot__comp_compression_lane_handoff_v1.json",
    "reports__constitution__btrack_pilot__comp_atom_track_b_closure_v1.json",
)


async def _push_lens(
    session: ClientSession,
    lens: str,
    notebook_id: str,
    *,
    dry_run: bool,
    sleep_s: float,
    max_files: int,
) -> list[dict]:
    rows: list[dict] = []
    lens_dir = PACK_ROOT / lens
    if not lens_dir.is_dir():
        return [{"lens": lens, "file": None, "success": False, "error": "missing_dir"}]

    paths = sorted(p for p in lens_dir.iterdir() if p.is_file())
    if max_files > 0:
        pri = [p for p in paths if p.name in PRIORITY_FILENAMES]
        rest = [p for p in paths if p.name not in PRIORITY_FILENAMES]
        paths = pri + rest[: max(0, max_files - len(pri))]

    for path in paths:
        body = path.read_text(encoding="utf-8", errors="replace")
        parts = _chunks(body)
        for part_i, part in enumerate(parts):
            title = path.name if len(parts) == 1 else f"{path.name}__part{part_i}"
            row = {
                "lens": lens,
                "notebook_id": notebook_id,
                "file": path.name,
                "part": part_i,
                "title": title,
                "chars": len(part),
                "success": False,
                "error": None,
            }
            if dry_run:
                row["success"] = True
                row["dry_run"] = True
                rows.append(row)
                continue
            try:
                result = await session.call_tool(
                    "add_source",
                    {
                        "type": "text",
                        "content": part,
                        "title": title[:120],
                        "notebook_id": notebook_id,
                    },
                )
                parsed = _parse_result(result)
                row.update(parsed)
            except Exception as exc:  # noqa: BLE001
                row["error"] = str(exc)
            rows.append(row)
            print(json.dumps(row, ensure_ascii=False), flush=True)
            if sleep_s > 0:
                time.sleep(sleep_s)
    return rows


async def run_all(
    *, dry_run: bool, sleep_s: float, lenses: list[str], max_files: int
) -> dict:
    all_rows: list[dict] = []
    async with stdio_client(_server_params()) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            health = await session.call_tool("get_health", {})
            auth = False
            for block in health.content or []:
                t = getattr(block, "text", "") or ""
                if t.strip().startswith("{"):
                    h = json.loads(t)
                    d = h.get("data", h)
                    auth = d.get("authenticated") is True
            if not auth and not dry_run:
                return {"error": "authenticated_false", "rows": []}

            for lens in lenses:
                nb = LENS_NOTEBOOK[lens]
                all_rows.extend(
                    await _push_lens(
                        session,
                        lens,
                        nb,
                        dry_run=dry_run,
                        sleep_s=sleep_s,
                        max_files=max_files,
                    )
                )

    ok = sum(1 for r in all_rows if r.get("success"))
    fail = sum(1 for r in all_rows if not r.get("success"))
    return {
        "schema": "comp_nl_auto_upload_result_v1",
        "generated_at_utc": _utc(),
        "commander_approved": True,
        "method": "notebooklm_mcp_add_source_text",
        "script": "scripts/push_comp_btrack_nl_mcp_v1.py",
        "ok": ok,
        "fail": fail,
        "success": fail == 0 and ok > 0,
        "rows": all_rows,
    }


def _cursor_mcp_already_running() -> bool:
    """Avoid second notebooklm-mcp stdio stack while Cursor MCP is active."""
    try:
        import subprocess

        out = subprocess.check_output(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "(Get-CimInstance Win32_Process -Filter \"name='node.exe'\" | "
                "Where-Object { $_.CommandLine -match 'notebooklm-mcp' }).Count",
            ],
            text=True,
            timeout=15,
        )
        return int(out.strip() or "0") >= 1
    except Exception:
        return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--sleep", type=float, default=2.0)
    parser.add_argument(
        "--max-files",
        type=int,
        default=3,
        help="Max files per lens (default 3 SSOT only). Use 0 for unlimited (not recommended).",
    )
    parser.add_argument(
        "--force-second-mcp",
        action="store_true",
        help="Allow spawning stdio MCP while Cursor MCP may already be running (NOT recommended).",
    )
    parser.add_argument(
        "--lenses",
        default="COMPRESSION_BTRACK,IJEOMA_BTRACK",
        help="comma-separated lens folder names",
    )
    args = parser.parse_args()

    if not args.dry_run and not args.force_second_mcp and _cursor_mcp_already_running():
        print(
            json.dumps(
                {
                    "error": "notebooklm_mcp_already_running",
                    "hint": "Cursor MCP is active. Use IDE add_source for <=3 files, or "
                    "MCP off + new chat, or nlm CLI one file at a time. "
                    "See reports/constitution/btrack_pilot/comp_nl_auto_upload_aborted_v1.json",
                },
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 3
    lenses = [x.strip() for x in args.lenses.split(",") if x.strip()]
    doc = asyncio.run(
        run_all(
            dry_run=args.dry_run,
            sleep_s=args.sleep,
            lenses=lenses,
            max_files=args.max_files,
        )
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"wrote": str(OUT.relative_to(ROOT)), "ok": doc.get("ok"), "fail": doc.get("fail")},
            ensure_ascii=False,
        )
    )
    if doc.get("error"):
        return 2
    return 0 if doc.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
