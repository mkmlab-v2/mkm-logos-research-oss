"""Smoke tests for gold fixture extension merge."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MERGE = ROOT / "scripts/merge_logos_gold_query_eval_extension_v1.py"
GOLD = ROOT / "docs/final/fixtures/logos_gold_query_eval_v1.json"
EXT = ROOT / "docs/final/fixtures/logos_gold_query_eval_extension_v1.json"


def test_merge_extension_dry_run() -> None:
    assert EXT.is_file()
    proc = subprocess.run(
        [sys.executable, str(MERGE), "--dry-run"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(proc.stdout.strip().splitlines()[-1])
    assert doc["ok"] is True
    assert doc["item_count"] >= 24


def test_extension_pack_has_twelve_items() -> None:
    doc = json.loads(EXT.read_text(encoding="utf-8-sig"))
    assert doc["schema"] == "logos_gold_query_eval_extension_v1"
    assert len(doc["items"]) == 12
