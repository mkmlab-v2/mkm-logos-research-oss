"""P3 root generator lib — router probe (offline)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.p3_root_generator_lib_v1 import router_probe_metrics, shallow_router_slice  # noqa: E402

BASELINE = REPO / "reports/constitution/btrack_pilot/master_codebook_lexicon_v1_41658_rows_latest.json"
ROUTER_PROBE = REPO / "tests/fixtures/p3_root_router_probe_v1.json"


@pytest.mark.skipif(not BASELINE.is_file(), reason="41658 baseline export missing")
def test_router_probe_metrics_shape():
    fixture = json.loads(ROUTER_PROBE.read_text(encoding="utf-8"))
    doc = router_probe_metrics(BASELINE, fixture)
    assert doc["probe_count"] >= 1
    assert 0.0 <= doc["domain_router_hit_rate"] <= 1.0
    assert 0.0 <= doc["lexicon_token_hit_rate"] <= 1.0


def test_shallow_router_slice_skipped_offline():
    doc = shallow_router_slice(skip_ollama=True)
    assert doc.get("skipped") is True
    assert doc.get("router_hit_rate") is None or doc.get("status") == "skipped"
