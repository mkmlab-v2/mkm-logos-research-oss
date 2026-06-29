"""CONSTITUTION pointer PR draft builder tests."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts/build_a_code_constitution_pointer_pr_draft_v1.py"
MIGRATION = ROOT / "docs/final/artifacts/a_code_constitution_worklist_migration_draft_v1.json"


def _load():
    spec = importlib.util.spec_from_file_location("pr_draft", BUILD)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_pr_draft_human_only() -> None:
    mod = _load()
    migration = json.loads(MIGRATION.read_text(encoding="utf-8"))
    doc = mod.build_pr_draft(migration=migration, lane={"lane_status": "OPERATOR_ASSIST_FIXED"})
    assert doc.get("human_pr_required") is True
    assert doc.get("status") == "draft_for_human_pr"
    assert doc.get("track_wall", {}).get("constitution_auto_edit") is False
    md = mod.render_markdown(doc)
    assert "human PR only" in md
    assert "Explicit NOT migrated" in md


def test_pr_draft_cli(tmp_path: Path) -> None:
    out_md = tmp_path / "draft.md"
    out_json = tmp_path / "draft.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(BUILD),
            "--out-md",
            str(out_md),
            "--out-json",
            str(out_json),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert out_md.is_file()
    assert "CONSTITUTION table row" in out_md.read_text(encoding="utf-8")
