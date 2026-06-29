"""Regression: logos lens batch must not emit sample-* verse_id stubs."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BATCH = ROOT / "data" / "logos" / "4lens_batch_real_verses_v1.json"
LENS = ROOT / "docs" / "final" / "artifacts" / "logos_independent_lens_latest.json"


def test_real_batch_builder_no_sample_ids() -> None:
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_logos_4lens_batch_from_corpus_v1.py"),
            "--from-gold-q01",
            "--out",
            str(BATCH),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert r.returncode == 0, r.stderr or r.stdout
    rows = json.loads(BATCH.read_text(encoding="utf-8"))
    assert isinstance(rows, list) and rows
    for row in rows:
        vid = row.get("verse_id", "")
        assert isinstance(vid, str) and vid
        assert not vid.startswith("sample-"), vid
        p1 = row.get("pipeline1_simple_4d") or {}
        v4 = p1.get("vector_4d") or {}
        assert set(v4.keys()) >= {"S", "L", "K", "M"}


def test_logos_lens_artifact_rejects_sample_when_present() -> None:
    if not LENS.is_file():
        return
    doc = json.loads(LENS.read_text(encoding="utf-8"))
    refs = doc.get("evidence_refs") or []
    for ref in refs:
        if not isinstance(ref, dict):
            continue
        vid = ref.get("verse_id")
        if isinstance(vid, str) and vid:
            assert not vid.startswith("sample-"), vid
