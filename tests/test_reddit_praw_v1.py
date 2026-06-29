"""Tests for Reddit PRAW post helper (offline)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from post_reddit_praw_v1 import PACKS, resolve_flair_id  # noqa: E402


class _FakeFlair:
    def __init__(self, choices):
        self.link_templates = self
        self._choices = choices

    def user_selectable(self):
        return self._choices


class _FakeSub:
    def __init__(self, choices):
        self.flair = _FakeFlair(choices)


def test_resolve_flair_id_case_insensitive():
    sub = _FakeSub([{"text": "Discussion", "id": "abc123"}])
    assert resolve_flair_id(sub, "discussion") == "abc123"


def test_resolve_flair_id_missing():
    sub = _FakeSub([{"text": "News", "id": "n1"}])
    assert resolve_flair_id(sub, "Discussion") is None


def test_packs_exist_on_disk():
    for pack in PACKS.values():
        assert pack["title"].is_file(), pack["title"]
        assert pack["body"].is_file(), pack["body"]
