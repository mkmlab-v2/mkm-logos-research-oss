"""P21 router regression bundle — P15 bloom guard + full gold fixture."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BUNDLE_OUT = ROOT / "reports/logos_router_regression_bundle_v1_latest.json"
SLICE_PUBLIC = ROOT / "projects/mkm/mkm-life/public/data/logos_cosmic_anchor_graph_bloom_slice_v1.json"


@pytest.fixture(scope="module")
def bundle_chain() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_logos_router_regression_bundle_v1.py",
            "--skip-pytest",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_bundle_report_pass(bundle_chain: None) -> None:
    report = json.loads(BUNDLE_OUT.read_text(encoding="utf-8-sig"))
    assert report["chain_pass"] is True
    assert report["bloom_cap"]["artifact"] == 128
    assert report["bloom_cap"]["unchanged"] is True
    assert report["gold_eval"]["gold_required_all_pass"] is True


def test_p15_does_not_rollback_bloom(bundle_chain: None) -> None:
    doc = json.loads(SLICE_PUBLIC.read_text(encoding="utf-8"))
    assert doc.get("resonance_cap") == 128
    assert len(doc.get("resonance_edges_top") or []) == 128


def test_router_hit_rate_one(bundle_chain: None) -> None:
    eval_doc = json.loads(
        (ROOT / "docs/final/artifacts/logos_narrative_path_eval_v1_latest.json").read_text(encoding="utf-8-sig")
    )
    assert eval_doc["summary"]["router_hit_rate"] == 1.0
