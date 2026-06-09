# -*- coding: utf-8 -*-
"""Regression: coding intent 3-point link PoC."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "record_coding_intent_link_v1.py"
_SCHEMA = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "final"
    / "schemas"
    / "coding_intent_link_v1.schema.json"
)


def _load_mod():
    spec = importlib.util.spec_from_file_location("record_coding_intent_link_v1", _SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _central_with_checkpoint(tmp_path: Path) -> Path:
    central = tmp_path / "CENTRAL_AGENT_MEMORY_V1.md"
    central.write_text(
        """# C

<!-- ATHENA_CHECKPOINT_V1_START -->
- **2026-06-09T16:24:02Z** — 의도DB 테스트 체크포인트
<!-- ATHENA_CHECKPOINT_V1_END -->
""",
        encoding="utf-8",
    )
    return central


def test_build_record_link_ok_with_supplied_gate(tmp_path: Path):
    mod = _load_mod()
    root = tmp_path
    central = _central_with_checkpoint(root)

    doc = mod.build_record(
        root=root,
        central_path=central,
        mission_id="test-mission",
        note=None,
        run_gate=False,
        gate_command=None,
        gate_exit_code=0,
        git_head_sha="abc1234deadbeef" * 4,
        git_branch="feat/intent-link",
        git_subject="feat: intent link poc",
        git_dirty=False,
        checkpoint_stamp="2026-06-09T16:24:02Z",
        checkpoint_message="의도DB 테스트",
    )
    assert doc["schema"] == "coding_intent_link_v1"
    assert doc["research_only"] is True
    assert doc["link_ok"] is True
    assert doc["gate"]["ok"] is True
    assert len(doc["link_id"]) == 16


def test_latest_checkpoint_parses_first_bullet(tmp_path: Path):
    mod = _load_mod()
    central = _central_with_checkpoint(tmp_path)
    cp = mod._latest_checkpoint(central, root=tmp_path)
    assert cp["present"] is True
    assert cp["stamp_utc"] == "2026-06-09T16:24:02Z"
    assert "의도DB" in cp["message"]


def test_parse_numstat_and_merge():
    mod = _load_mod()
    text = "3\t1\tscripts/foo.py\n10\t0\tdocs/bar.md"
    files = mod._parse_numstat(text)
    assert len(files) == 2
    assert files[0]["path"] == "scripts/foo.py"
    merged = mod._merge_file_stats(files, [{"path": "scripts/foo.py", "insertions": 2, "deletions": 0}])
    foo = next(r for r in merged if r["path"] == "scripts/foo.py")
    assert foo["insertions"] == 5
    assert foo["deletions"] == 1


def test_parse_diff_hunks_caps_and_intent_ref():
    mod = _load_mod()
    diff = """diff --git a/scripts/x.py b/scripts/x.py
+++ b/scripts/x.py
@@ -10,3 +10,4 @@ def foo():
@@ -20,1 +21,2 @@ def bar():
"""
    hunks = mod._parse_diff_hunks(diff, intent_ref="checkpoint msg", max_hunks=1)
    assert len(hunks) == 1
    assert hunks[0]["path"] == "scripts/x.py"
    assert hunks[0]["old_start"] == 10
    assert hunks[0]["intent_ref"] == "checkpoint msg"


def test_build_record_include_diff_override(tmp_path: Path):
    mod = _load_mod()
    root = tmp_path
    central = _central_with_checkpoint(root)
    files = [{"path": "scripts/a.py", "insertions": 5, "deletions": 1}]
    hunks = [
        {
            "path": "scripts/a.py",
            "old_start": 1,
            "old_lines": 2,
            "new_start": 1,
            "new_lines": 3,
            "intent_ref": "의도DB 테스트 체크포인트",
        }
    ]
    doc = mod.build_record(
        root=root,
        central_path=central,
        mission_id=None,
        note=None,
        run_gate=False,
        gate_command=None,
        gate_exit_code=0,
        git_head_sha="abc1234deadbeef" * 4,
        git_branch="main",
        git_subject="smoke",
        git_dirty=True,
        checkpoint_stamp="2026-06-09T16:24:02Z",
        checkpoint_message="의도DB 테스트 체크포인트",
        include_diff=True,
        diff_files_override=files,
        diff_hunks_override=hunks,
    )
    assert "diff_summary" in doc
    assert doc["diff_summary"]["scope"] == "working_tree"
    assert doc["diff_summary"]["files"][0]["intent_ref"] == "의도DB 테스트 체크포인트"
    assert doc["diff_summary"]["hunks"][0]["new_lines"] == 3


@pytest.mark.skipif(not _SCHEMA.is_file(), reason="schema missing")
def test_schema_validates_example_doc():
    jsonschema = pytest.importorskip("jsonschema")
    mod = _load_mod()
    root = Path(__file__).resolve().parents[1]
    doc = mod.build_record(
        root=root,
        central_path=root / "docs" / "final" / "CENTRAL_AGENT_MEMORY_V1.md",
        mission_id="schema-smoke",
        note=None,
        run_gate=False,
        gate_command=None,
        gate_exit_code=0,
        git_head_sha="abc1234deadbeef" * 4,
        git_branch="main",
        git_subject="smoke",
        git_dirty=False,
        checkpoint_stamp="2026-06-09T00:00:00Z",
        checkpoint_message="smoke",
    )
    schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))
    jsonschema.validate(doc, schema)
