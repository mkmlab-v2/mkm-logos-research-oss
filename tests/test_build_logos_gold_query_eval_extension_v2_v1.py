"""Smoke tests for gold extension v2 builder (holdout paraphrases)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/build_logos_gold_query_eval_extension_v2_v1.py"
GOLD = ROOT / "docs/final/fixtures/logos_gold_query_eval_v1.json"


def test_build_extension_v2(tmp_path: Path) -> None:
    out = tmp_path / "extension_v2.json"
    proc = subprocess.run(
        [sys.executable, str(BUILDER), "--out", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8-sig"))
    assert doc["schema"] == "logos_gold_query_eval_extension_v2"
    assert len(doc["items"]) == 24
    ids = {str(x["id"]) for x in doc["items"]}
    assert "q25" in ids and "q48" in ids
    for item in doc["items"]:
        assert item.get("holdout_source_id")
        assert item.get("eval_tier") == "gold_required"


def test_merge_extension_v2_dry_run(tmp_path: Path) -> None:
    ext = tmp_path / "extension_v2.json"
    subprocess.run(
        [sys.executable, str(BUILDER), "--out", str(ext)],
        cwd=str(ROOT),
        check=True,
    )
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/merge_logos_gold_query_eval_extension_v1.py"),
            "--extension-json",
            str(ext),
            "--dry-run",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(proc.stdout.strip().splitlines()[-1])
    assert doc["ok"] is True
    assert doc["item_count"] >= 48
