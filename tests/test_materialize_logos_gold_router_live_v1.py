#!/usr/bin/env python3
"""Tests for logos gold router live materialize (P1-4)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIVE = ROOT / "scripts/materialize_logos_gold_router_live_v1.py"
LEGACY = ROOT / "scripts/materialize_logos_gold_router_canonical_v1.py"
ROUTER_Q02 = ROOT / "reports/magic_orb_insight_by_query/router_q02_latest.json"
GOLD = ROOT / "docs/final/fixtures/logos_gold_query_eval_v1.json"


def test_materialize_live_router_q02_canonical_verses(tmp_path: Path) -> None:
    out_manifest = tmp_path / "manifest.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(LIVE),
            "--query-id",
            "q02",
            "--promote-gold-prefix-first",
            "--out-json",
            str(out_manifest),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    body = json.loads(ROUTER_Q02.read_text(encoding="utf-8"))
    meta = body.get("materialize_meta") or {}
    assert meta.get("schema") == "logos_gold_router_live_materialize_v1"
    assert meta.get("post_hoc_canonical_skipped") is True
    assert body["verse_ids"][0] == "Jer.1.10"
    assert all(not str(v).startswith("verse_ref:") for v in body["verse_ids"])
    assert all(not str(s).startswith("node_verse_") for p in body.get("paths") or [] for s in (p.get("steps") or []))
    assert (body.get("policy") or {}).get("verse_ref_canonical_at_source") is True


def test_legacy_post_hoc_canonical_requires_flag() -> None:
    proc = subprocess.run(
        [sys.executable, str(LEGACY), "--query-id", "q02"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 2
    payload = json.loads(proc.stdout.strip().splitlines()[-1])
    assert payload.get("error") == "post_hoc_deprecated_use_live"


def test_live_materialize_manifest_ok() -> None:
    proc = subprocess.run(
        [sys.executable, str(LIVE), "--query-id", "q02", "--query-id", "q05"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    manifest = json.loads(
        (ROOT / "reports/logos_gold_router_live_materialize_v1_latest.json").read_text(encoding="utf-8")
    )
    assert manifest.get("ok") is True
    assert len(manifest.get("rows") or []) == 2
