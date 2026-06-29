from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ROUTER_MAP = ROOT / "data/commander/domain_prophecy_shallow_router_map_v1.json"
REGISTRY = ROOT / "data/commander/domain_prophecy_registry_v1.json"


def test_router_map_covers_all_registry_domains() -> None:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    map_doc = json.loads(ROUTER_MAP.read_text(encoding="utf-8"))
    reg_ids = {str(r["domain_id"]) for r in registry.get("domains") or []}
    map_ids = {str(r["domain_id"]) for r in map_doc.get("routes") or []}
    assert reg_ids == map_ids


def test_shallow_route_self_test_exit0() -> None:
    proc = subprocess.run(
        [sys.executable, "scripts/route_domain_prophecy_from_shallow_v1.py", "--self-test"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_smoke_coverage_gate_exit0() -> None:
    proc = subprocess.run(
        [sys.executable, "scripts/check_domain_prophecy_smoke_coverage_v1.py"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_weekly_digest_build_exit0() -> None:
    proc = subprocess.run(
        [sys.executable, "scripts/build_domain_prophecy_weekly_digest_v1.py"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    out = ROOT / "reports/domain_prophecy_weekly_digest_v1_latest.json"
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("send_gate") == "HOLD"
    assert doc.get("research_only") is True


def test_route_logos_candidates() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/route_domain_prophecy_from_shallow_v1.py",
            "--shallow-tag",
            "logos",
            "--text",
            "verse resolution graphrag insight",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    out = ROOT / "reports/domain_prophecy_shallow_route_v1_latest.json"
    doc = json.loads(out.read_text(encoding="utf-8"))
    ids = {c["domain_id"] for c in doc.get("candidates") or []}
    assert "logos_verse_resolution" in ids
