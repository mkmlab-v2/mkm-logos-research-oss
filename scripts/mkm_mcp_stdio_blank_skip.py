"""One-shot monkeypatch: MCP stdio ignores blank stdin lines (stray newlines).

Cursor / shells sometimes inject empty lines into the MCP stdio pipe; the stock
`mcp.server.stdio` treats each line as JSON-RPC and logs validation noise. Skipping
blank lines is safe because `JSONRPCMessage.model_validate_json` expects one
non-empty JSON object per line (same transport contract).
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from io import TextIOWrapper

import anyio
import anyio.lowlevel
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream

import mcp.types as types
from mcp.shared.message import SessionMessage


def apply_stdio_blank_line_patch() -> None:
    import mcp.server.stdio as ms

    if getattr(ms, "_mkm_blank_skip_patched", False):
        return
    setattr(ms, "_mkm_blank_skip_patched", True)

    @asynccontextmanager
    async def stdio_server(  # type: ignore[override]
        stdin: anyio.AsyncFile[str] | None = None,
        stdout: anyio.AsyncFile[str] | None = None,
    ):
        import sys

        if not stdin:
            stdin = anyio.wrap_file(TextIOWrapper(sys.stdin.buffer, encoding="utf-8"))
        if not stdout:
            stdout = anyio.wrap_file(TextIOWrapper(sys.stdout.buffer, encoding="utf-8"))

        read_stream_writer, read_stream = anyio.create_memory_object_stream(0)
        write_stream, write_stream_reader = anyio.create_memory_object_stream(0)

        async def stdin_reader():
            try:
                async with read_stream_writer:
                    async for line in stdin:
                        # PowerShell / some hosts emit UTF-8 BOM on "empty" writes (\ufeff\n) — not .strip() blank.
                        core = line.lstrip("\ufeff").strip()
                        if not core:
                            continue
                        try:
                            message = types.JSONRPCMessage.model_validate_json(core)
                        except Exception as exc:  # pragma: no cover — match upstream
                            await read_stream_writer.send(exc)
                            continue

                        session_message = SessionMessage(message)
                        await read_stream_writer.send(session_message)
            except anyio.ClosedResourceError:  # pragma: no cover
                await anyio.lowlevel.checkpoint()

        async def stdout_writer():
            try:
                async with write_stream_reader:
                    async for session_message in write_stream_reader:
                        json = session_message.message.model_dump_json(
                            by_alias=True, exclude_none=True
                        )
                        await stdout.write(json + "\n")
                        await stdout.flush()
            except anyio.ClosedResourceError:  # pragma: no cover
                await anyio.lowlevel.checkpoint()

        async with anyio.create_task_group() as tg:
            tg.start_soon(stdin_reader)
            tg.start_soon(stdout_writer)
            yield read_stream, write_stream

    ms.stdio_server = stdio_server  # type: ignore[assignment]
    # FastMCP does `from mcp.server.stdio import stdio_server` at import time — re-bind
    # so run_stdio_async uses the patched context manager, not the original.
    import mcp.server.fastmcp.server as fastmcp_server_mod

    fastmcp_server_mod.stdio_server = stdio_server  # type: ignore[assignment]
