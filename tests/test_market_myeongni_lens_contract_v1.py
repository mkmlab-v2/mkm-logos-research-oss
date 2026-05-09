"""CONTRACT + JSON Schema path presence for Market Myeongni lens v1 (P0 / CI gate alignment)."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs" / "final" / "artifacts" / "MARKET_MYEONGNI_LENS_V1_CONTRACT.json"


def test_market_myeongni_contract_paths_resolve() -> None:
    assert CONTRACT.is_file(), "MARKET_MYEONGNI_LENS_V1_CONTRACT.json must exist (SSOT pointer bundle)."
    doc = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert doc.get("artifact_schema") == "market_myeongni_lens_v1"

    schema_rel = doc.get("artifact_json_schema")
    assert isinstance(schema_rel, str) and schema_rel
    schema_path = (ROOT / schema_rel).resolve()
    assert schema_path.is_file(), schema_path

    for key in ("policy_file", "engine_module", "runner"):
        rel = doc.get(key)
        assert isinstance(rel, str) and rel
        p = (ROOT / Path(rel)).resolve()
        assert p.is_file(), (key, p)
