"""Tests for LTM P4 scale closure and prism gap report ([HYPO] / B-track)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from check_ltm_p4_scale_closure_v1 import TRADING_GUARD_IDS  # noqa: E402
from mkm_long_term_memory_graph_lib_v1 import CONCEPT_BY_ID  # noqa: E402
from report_ltm_prism_id_gaps_v1 import build_report  # noqa: E402


def test_trading_guard_concepts_present() -> None:
    for cid in TRADING_GUARD_IDS:
        assert cid in CONCEPT_BY_ID


def test_prism_gap_report_schema() -> None:
    doc = build_report(ROOT)
    assert doc["schema"] == "ltm_prism_id_gaps_v1"
    assert doc["concept_count"] >= 54
    assert isinstance(doc["path_match_suggestions"], list)


def test_route_trading_guard_subgraph(tmp_path: Path) -> None:
    from mkm_long_term_memory_graph_lib_v1 import build_graph_document, route_concepts_by_query

    from tests.test_mkm_long_term_memory_graph_v1 import _write_min_ssot

    _write_min_ssot(tmp_path)
    doc = build_graph_document(tmp_path)
    routed = route_concepts_by_query(doc, "vps pm2 go nogo human approval live trading")
    ids = {cid for cid, _ in routed}
    assert ids.intersection(TRADING_GUARD_IDS)
