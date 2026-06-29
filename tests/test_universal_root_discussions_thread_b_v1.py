"""Universal Root GTM — Thread B discussions dry-run gate."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
THREAD_B = ROOT / "scripts/post_universal_root_discussions_thread_b_v1.py"
PASTE_TITLE = ROOT / "reports/human_paste/universal_root_discussions_thread_b_title.txt"
PASTE_BODY = ROOT / "reports/human_paste/universal_root_discussions_thread_b_body.md"


def test_thread_b_paste_files_exist():
    assert PASTE_TITLE.is_file()
    assert PASTE_BODY.is_file()
    assert PASTE_TITLE.read_text(encoding="utf-8-sig").strip()
    assert len(PASTE_BODY.read_text(encoding="utf-8-sig").strip()) > 200


def test_thread_b_dry_run():
    if not THREAD_B.is_file():
        return
    proc = subprocess.run(
        [sys.executable, str(THREAD_B), "--dry-run"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout or proc.stderr
    payload = json.loads(proc.stdout)
    assert payload.get("ok") is True
    assert payload.get("dry_run") is True
    assert payload.get("gate") == "blocked_await_external_repro"


def test_gtm_chain_includes_thread_b_step():
    chain = ROOT / "scripts/run_universal_root_community_gtm_chain_v1.py"
    assert chain.is_file()
    text = chain.read_text(encoding="utf-8")
    assert "discussions_thread_b_dry_run" in text
