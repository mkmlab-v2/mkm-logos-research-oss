# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_apply_jsonl_encoder_promotion_dry_run() -> None:
    cp = subprocess.run(
        [sys.executable, str(ROOT / "scripts/apply_logos_jsonl_4d_encoder_promotion_v1.py"), "--dry-run"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(cp.stdout.strip().splitlines()[-1])
    assert doc["ok"] is True
    assert doc["updated_rows"] == 41


def test_corpus_promotion_dry_run() -> None:
    cp = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_logos_4d_corpus_promotion_v1.py"), "--dry-run"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(cp.stdout.strip().splitlines()[-1])
    assert doc["ok"] is True
