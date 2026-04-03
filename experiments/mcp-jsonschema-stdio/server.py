"""
Minimal stdio MCP server: JSON Schema (Draft 2020-12) + runtime validation.

Uses FastMCP (ships with `mcp` PyPI package). Run:
  py server.py

Not wired to production ops or trading.
"""

from __future__ import annotations

import json
from typing import Annotated

from jsonschema import Draft202012Validator, ValidationError
from mcp.server.fastmcp import FastMCP
from pydantic import Field

SERVER_NAME = "mcp-jsonschema-sentiment-stub"

# Shared contract: MCP tool schema and runtime check use the same JSON Schema
RATIO_SCHEMA: dict = {
    "type": "object",
    "required": ["ratio"],
    "additionalProperties": False,
    "properties": {
        "ratio": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
            "description": "Scalar in [0,1], e.g. panic or relief score",
        }
    },
}

_validator = Draft202012Validator(RATIO_SCHEMA)

mcp = FastMCP(SERVER_NAME)


@mcp.tool()
def sentiment_ratio(
    ratio: Annotated[
        float,
        Field(ge=0.0, le=1.0, description="Scalar in [0,1] (MCP schema + jsonschema runtime)"),
    ],
) -> str:
    """Validate `ratio` with JSON Schema (guardrail); return JSON text."""
    data = {"ratio": ratio}
    try:
        _validator.validate(data)
    except ValidationError as e:
        return json.dumps({"ok": False, "error": e.message})
    return json.dumps({"ok": True, "ratio": ratio, "validated": "jsonschema+D202012"})


if __name__ == "__main__":
    mcp.run(transport="stdio")
