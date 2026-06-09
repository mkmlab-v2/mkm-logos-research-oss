# -*- coding: utf-8 -*-
"""Regression: coding intent PR manifest PoC."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_coding_intent_pr_manifest_v1.py"
_SCHEMA = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "final"
    / "schemas"
    / "coding_intent_pr_manifest_v1.schema.json"
)


def _load_mod():
    spec = importlib.util.spec_from_file_location("build_coding_intent_pr_manifest_v1", _SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_pick_checkpoint_prefers_prior_stamp():
    mod = _load_mod()
    cps = [
        {"stamp_utc": "2026-06-09T17:00:00Z", "message": "newer"},
        {"stamp_utc": "2026-06-09T16:00:00Z", "message": "older"},
    ]
    picked = mod.pick_checkpoint_for_commit("2026-06-09T16:30:00Z", cps)
    assert picked is not None
    assert picked["message"] == "older"


def test_build_manifest_coverage_counts():
    mod = _load_mod()
    commits = [
        {"sha": "abc1234" * 8, "subject": "feat: a", "author_iso": "2026-06-09T16:30:00+00:00"},
        {"sha": "def5678" * 8, "subject": "feat: b", "author_iso": "2026-06-09T17:30:00+00:00"},
    ]
    checkpoints = [{"stamp_utc": "2026-06-09T16:00:00Z", "message": "cp one"}]
    link_index = {
        commits[0]["sha"]: {
            "link_id": "link1",
            "link_ok": True,
            "git": {"head_sha": commits[0]["sha"]},
        }
    }
    doc = mod.build_manifest(
        base_ref="gitea/main",
        head_sha=commits[0]["sha"],
        branch="feat/test",
        commits=commits,
        checkpoints=checkpoints,
        link_index=link_index,
    )
    assert doc["schema"] == "coding_intent_pr_manifest_v1"
    assert doc["research_only"] is True
    assert doc["commit_count"] == 2
    assert doc["coverage"]["commits_with_link"] == 1
    assert doc["coverage"]["commits_with_checkpoint"] == 2
    assert doc["rows"][0]["intent_ref"] == "cp one"
    assert doc["rows"][0]["link_id"] == "link1"


@pytest.mark.skipif(not _SCHEMA.is_file(), reason="schema missing")
def test_schema_validates_manifest_doc():
    jsonschema = pytest.importorskip("jsonschema")
    mod = _load_mod()
    doc = mod.build_manifest(
        base_ref="main",
        head_sha="abc1234" * 8,
        branch="main",
        commits=[{"sha": "abc1234" * 8, "subject": "smoke", "author_iso": None}],
        checkpoints=[],
        link_index={},
    )
    schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))
    jsonschema.validate(doc, schema)
