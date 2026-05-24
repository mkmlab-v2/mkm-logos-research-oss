"""M24: RQ-019 ops slice + regression chain."""

from __future__ import annotations


def test_rq019_ops_slice():
    from scripts.build_mkm_inter_agent_rq019_ops_slice_v1 import build_ops_slice

    doc = build_ops_slice()
    assert doc.get("ok")
    assert doc.get("readiness", {}).get("language_dev_m23_ready") is True


def test_rq019_regression_chain_skip_pytest():
    from scripts.run_mkm_inter_agent_rq019_regression_chain_v1 import run_chain

    doc = run_chain(skip_pytest=True, quick=True)
    assert doc.get("ok")
    assert all(s.get("ok") for s in doc.get("steps") or [])
