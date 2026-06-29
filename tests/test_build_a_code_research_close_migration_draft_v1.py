"""A-code RESEARCH close migration draft tests."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts/build_a_code_research_close_migration_draft_v1.py"


def _load():
    spec = importlib.util.spec_from_file_location("migration_draft", BUILD)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_migration_draft_agent_auto_apply_forbidden() -> None:
    mod = _load()
    doc = mod.build()
    assert doc.get("agent_auto_apply") is False
    assert doc.get("research_only") is True
    assert doc.get("hypothesis_tier") == "B"
    rows = doc.get("suggested_table_rows") or []
    assert len(rows) == 3
    for rq in ("RQ-028", "RQ-029", "RQ-031"):
        assert any(rq in r and "**CLOSED**" in r for r in rows)


def test_migration_draft_cli(tmp_path: Path) -> None:
    out_json = tmp_path / "draft.json"
    out_md = tmp_path / "draft.md"
    proc = subprocess.run(
        [sys.executable, str(BUILD), "--out-json", str(out_json), "--out-md", str(out_md)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(out_json.read_text(encoding="utf-8"))
    assert doc.get("schema") == "a_code_research_close_migration_draft_v1"
    assert out_md.read_text(encoding="utf-8").startswith("# A-code RESEARCH close migration draft")
