"""Validate NotebookLM lens pack push map template JSON shape."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "docs" / "final" / "notebooklm_lens_pack_push_map_v1.template.json"

REQUIRED_LENS = (
    "OPS_COMMAND_ANCHOR",
    "LTM_GRAPH_OPS",
    "TRACKC_BIZ",
    "LENS_MYEONGNI",
    "LENS_SASANG",
    "LENS_LOGOS",
    "MKM_CORE_FACT",
    "COMPRESSION_BTRACK",
)


def test_lens_pack_push_map_template_schema() -> None:
    data = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    assert data.get("schema") == "notebooklm_lens_pack_push_map_v1"
    inner = data.get("lens_notebook_id")
    assert isinstance(inner, dict)
    for k in REQUIRED_LENS:
        assert k in inner, f"missing lens key {k}"
        v = inner[k]
        assert isinstance(v, str) and len(v) == 36 and v.count("-") == 4, f"bad uuid for {k}: {v!r}"
