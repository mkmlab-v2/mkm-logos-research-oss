from __future__ import annotations

import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_POINTER = _ROOT / "docs" / "final" / "MANSE_PRECISION_RUNTIME_POINTER_V1.json"


def test_manse_precision_pointer_exists_and_schema() -> None:
    assert _POINTER.is_file(), f"missing {_POINTER}"
    doc = json.loads(_POINTER.read_text(encoding="utf-8"))
    assert doc.get("schema") == "manse_precision_runtime_pointer_v1"
    assert doc.get("official_wiring", {}).get("agent_precision_path") == "B"
    assert doc.get("official_wiring", {}).get("transport") == "mcp_stdio"
    assert doc.get("cursor_mcp", {}).get("server_identifier") == "project-0-workspace-athena-manseryeok"
    assert "calculate_saju" in (doc.get("cursor_mcp", {}).get("tools") or [])


def test_precision_mcp_runtime_metadata() -> None:
    from tools.myeongni.manseryeok_provenance import precision_mcp_runtime_metadata

    m = precision_mcp_runtime_metadata()
    assert m["manseryeok_model"] == "mcp_athena_calculate_saju"
    assert "MANSE_PRECISION_RUNTIME_POINTER" in m["manseryeok_provenance_note"]
    assert "Path B" in m["manseryeok_provenance_note"]


def test_load_manse_precision_runtime_pointer() -> None:
    from tools.myeongni.manseryeok_provenance import load_manse_precision_runtime_pointer

    doc = load_manse_precision_runtime_pointer(_ROOT)
    assert doc is not None
    assert doc.get("official_wiring", {}).get("transport") == "mcp_stdio"
