#!/usr/bin/env python3
"""MKM unified MCP (stdio): prophecy registry Fact-Lock slice + mkm_compressed_payload_v1 helpers.

Does not replace project-0-workspace-compression-server; adds thin registry/payload tools for agents.

Cursor user config: in `%APPDATA%/Cursor/User/mcp.json` this process is typically the server key
**mkm-unified-hub** (command py -u …/scripts/mkm_unified_mcp.py, cwd repo root). SSOT:
`docs/final/artifacts/MKM_MCP_STDIO_POINTER_V1.json`.

Register in Cursor Settings → MCP (stdio). Do **not** run interactively in a plain terminal:
empty lines on stdin become invalid JSON-RPC and spam errors.

Env:
  MKM_PROPHECY_REGISTRY_PATH — override registry JSON (default: docs/final/artifacts/general_prophecy_latest.json)
  MKM_MCP_FORCE_STDIO=1 — allow stdio even when stdin is a TTY (debug only)

Deps: pip install mcp jsonschema pydantic (see scripts/requirements-mkm-mcp.txt)
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Annotated, Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PAYLOAD_SCHEMA_PATH = ROOT / "docs" / "final" / "schemas" / "mkm_compressed_payload_v1.schema.json"


def default_registry_path() -> Path:
    override = os.environ.get("MKM_PROPHECY_REGISTRY_PATH", "").strip()
    if override:
        return Path(override)
    return ROOT / "docs" / "final" / "artifacts" / "general_prophecy_latest.json"


def load_registry_doc(path: Path | None = None) -> dict[str, Any]:
    p = path or default_registry_path()
    if not p.is_file():
        raise FileNotFoundError(f"registry not found: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def _payload_validator():
    from jsonschema import Draft7Validator

    raw = json.loads(PAYLOAD_SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft7Validator.check_schema(raw)
    return Draft7Validator(raw)


_v = None


def get_payload_validator():
    global _v
    if _v is None:
        _v = _payload_validator()
    return _v


def validate_payload_dict(data: dict[str, Any]) -> tuple[bool, str]:
    try:
        get_payload_validator().validate(data)
    except Exception as e:
        return False, str(e)
    return True, "ok"


try:
    from mcp.server.fastmcp import FastMCP
    from pydantic import Field
except ImportError as e:  # pragma: no cover
    raise SystemExit(
        "Missing deps: pip install -r scripts/requirements-mkm-mcp.txt\n" + str(e)
    ) from e

SERVER_NAME = "mkm-unified-hub"
mcp = FastMCP(SERVER_NAME)


@mcp.tool()
def prophecy_registry_summary() -> str:
    """Fact-Lock: load general_prophecy registry JSON; return schema, question_count, question_ids (cap 120), paths."""
    try:
        doc = load_registry_doc()
    except FileNotFoundError as e:
        return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)
    qs = doc.get("questions") or []
    ids: list[str] = []
    for q in qs:
        if isinstance(q, dict) and isinstance(q.get("question_id"), str):
            ids.append(q["question_id"])
    out = {
        "ok": True,
        "registry_path": str(default_registry_path()),
        "schema": doc.get("schema"),
        "research_rail": doc.get("research_rail"),
        "generated_at_utc": doc.get("generated_at_utc"),
        "question_count": len(ids),
        "question_ids": ids[:120],
        "truncated_id_list": len(ids) > 120,
    }
    return json.dumps(out, ensure_ascii=False, indent=2)


@mcp.tool()
def prophecy_get_question(
    question_id: Annotated[str, Field(description="Must match an existing question_id in the registry.")],
) -> str:
    """Return one question object as JSON, or error if unknown question_id (exit semantics as JSON)."""
    try:
        doc = load_registry_doc()
    except FileNotFoundError as e:
        return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)
    for q in doc.get("questions") or []:
        if isinstance(q, dict) and q.get("question_id") == question_id:
            return json.dumps({"ok": True, "question": q}, ensure_ascii=False, indent=2)
    return json.dumps(
        {"ok": False, "error": f"unknown question_id: {question_id!r}"},
        ensure_ascii=False,
    )


@mcp.tool()
def mkm_payload_validate(
    payload_json: Annotated[str, Field(description="Full JSON object as a string (mkm_compressed_payload_v1).")],
) -> str:
    """Validate payload against docs/final/schemas/mkm_compressed_payload_v1.schema.json."""
    try:
        data = json.loads(payload_json)
    except json.JSONDecodeError as e:
        return json.dumps({"ok": False, "error": f"invalid JSON: {e}"}, ensure_ascii=False)
    if not isinstance(data, dict):
        return json.dumps({"ok": False, "error": "payload must be a JSON object"}, ensure_ascii=False)
    ok, msg = validate_payload_dict(data)
    return json.dumps({"ok": ok, "detail": msg}, ensure_ascii=False)


@mcp.tool()
def mkm_payload_build(
    text_effective: Annotated[str, Field(description="Primary context string for the agent.")],
    payload_kind: Annotated[
        str,
        Field(
            description="One of: lossy_summary, lossless_excerpt, code_reference, registry_pointer, prophecy_brief_slice"
        ),
    ],
    source_kind: Annotated[
        str,
        Field(description="One of: file_path, artifact_path, inline, mcp_tool"),
    ],
    source_path: Annotated[
        str | None,
        Field(description="Optional path string when source_kind is file_path or artifact_path."),
    ] = None,
    token_estimate: Annotated[int | None, Field(description="Optional non-negative token estimate.")] = None,
    fidelity_hint: Annotated[float | None, Field(description="Optional 0..1 fidelity hint.")] = None,
    compression_ratio: Annotated[float | None, Field(description="Optional 0..1 compression ratio.")] = None,
    warnings_json: Annotated[
        str | None,
        Field(description='Optional JSON array of strings, e.g. ["not for execution"]'),
    ] = None,
) -> str:
    """Build and validate a mkm_compressed_payload_v1 envelope; returns JSON including sha256 of text_effective."""
    source: dict[str, Any] = {"kind": source_kind}
    if source_path:
        source["path"] = source_path
    body: dict[str, Any] = {
        "schema": "mkm_compressed_payload_v1",
        "payload_kind": payload_kind,
        "text_effective": text_effective,
        "source": source,
    }
    if token_estimate is not None:
        body["token_estimate"] = int(token_estimate)
    if fidelity_hint is not None:
        body["fidelity_hint"] = float(fidelity_hint)
    if compression_ratio is not None:
        body["compression_ratio"] = float(compression_ratio)
    if warnings_json:
        try:
            w = json.loads(warnings_json)
            if isinstance(w, list):
                body["warnings"] = w
        except json.JSONDecodeError as e:
            return json.dumps({"ok": False, "error": f"warnings_json: {e}"}, ensure_ascii=False)
    ok, msg = validate_payload_dict(body)
    if not ok:
        return json.dumps({"ok": False, "validation": msg, "body": body}, ensure_ascii=False)
    return json.dumps({"ok": True, "payload": body}, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    if sys.stdin.isatty() and os.environ.get("MKM_MCP_FORCE_STDIO", "").strip() != "1":
        print(
            "mkm_unified_mcp: stdin is a TTY — this stdio MCP is meant to be started by Cursor (or another "
            "client) with a JSON-RPC pipe, not from an interactive shell.\n"
            "  → Add: py scripts/mkm_unified_mcp.py in Cursor MCP config (cwd: repo root).\n"
            "  → Debug: set MKM_MCP_FORCE_STDIO=1 to run here anyway.\n"
            "  → Tests: py -m pytest tests/test_mkm_unified_mcp.py",
            file=sys.stderr,
        )
        raise SystemExit(2)
    _scripts = Path(__file__).resolve().parent
    if str(_scripts) not in sys.path:
        sys.path.insert(0, str(_scripts))
    from mkm_mcp_stdio_blank_skip import apply_stdio_blank_line_patch

    apply_stdio_blank_line_patch()
    print(
        "[MKM-MCP] stdio blank-line skip patch active (stderr log; do not paste into shell)",
        file=sys.stderr,
        flush=True,
    )
    try:
        mcp.run(transport="stdio")
    except KeyboardInterrupt:
        # Cursor / terminal stop: avoid noisy asyncio/MCP stack traces on stderr.
        raise SystemExit(0) from None
    except asyncio.CancelledError:
        raise SystemExit(0) from None
