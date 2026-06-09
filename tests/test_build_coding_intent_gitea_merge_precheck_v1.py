# -*- coding: utf-8 -*-
"""Regression: gitea/internal merge precheck summary."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

_SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "build_coding_intent_gitea_merge_precheck_v1.py"
)
_SCHEMA = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "final"
    / "schemas"
    / "coding_intent_gitea_merge_precheck_v1.schema.json"
)


def _load_mod():
    spec = importlib.util.spec_from_file_location("build_coding_intent_gitea_merge_precheck_v1", _SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_build_precheck_ok_with_manifest_and_link():
    mod = _load_mod()
    manifest = {
        "base_ref": "gitea/main",
        "commit_count": 2,
        "coverage": {
            "commits_with_intent_ref": 2,
            "commits_with_link": 1,
            "commits_with_checkpoint": 2,
            "checkpoint_total": 5,
            "link_log_entries": 1,
        },
    }
    link = {"link_ok": False, "git": {"head_sha": "a" * 40}, "checkpoint": {"central_path": "x.md"}}
    doc = mod.build_precheck(
        integration_remote="gitea",
        base_ref="gitea/main",
        branch="feat/x",
        head_sha="a" * 40,
        ahead_commits=2,
        porcelain_lines=3,
        link_doc=link,
        manifest_doc=manifest,
        link_drift=[],
    )
    assert doc["publication_mode"] == "internal_first"
    assert doc["precheck_ok"] is True
    assert "working_tree_dirty" in doc["warnings"]


def test_build_precheck_blocker_missing_manifest():
    mod = _load_mod()
    doc = mod.build_precheck(
        integration_remote="gitea",
        base_ref="gitea/main",
        branch="main",
        head_sha="b" * 40,
        ahead_commits=1,
        porcelain_lines=0,
        link_doc=None,
        manifest_doc=None,
        link_drift=None,
        strict=True,
    )
    assert doc["precheck_ok"] is False
    assert "missing_pr_manifest" in doc["blockers"]


@pytest.mark.skipif(not _SCHEMA.is_file(), reason="schema missing")
def test_schema_validates_precheck_doc():
    jsonschema = pytest.importorskip("jsonschema")
    mod = _load_mod()
    doc = mod.build_precheck(
        integration_remote="gitea",
        base_ref="gitea/main",
        branch="main",
        head_sha="c" * 40,
        ahead_commits=0,
        porcelain_lines=0,
        link_doc={"link_ok": True},
        manifest_doc={"base_ref": "gitea/main", "commit_count": 0, "coverage": {}},
        link_drift=[],
    )
    schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))
    jsonschema.validate(doc, schema)
