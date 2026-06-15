"""[HYPO] KO premium CS WTT template overlay scan — B-track sandbox."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/run_ko_premium_cs_wtt_template_overlay_scan_v1.py"
ARTIFACT = ROOT / "docs/final/artifacts/ko_premium_cs_wtt_template_overlay_scan_v1_latest.json"
MANIFEST = ROOT / "data/compression/fixtures/zone_ko_premium_cs_wtt_overlay_scan_manifest_v1.json"


def test_wtt_overlay_manifest_excludes_icp() -> None:
    doc = json.loads(MANIFEST.read_text(encoding="utf-8"))
    paths = " ".join(doc.get("input_jsonl") or [])
    assert "icp-synthetic-operator" not in paths
    excluded = " ".join(doc.get("excluded_paths") or [])
    assert "icp-synthetic-operator" in excluded


def test_wtt_overlay_lib_tenant_hard_terms_only() -> None:
    from scripts.ko_premium_cs_wtt_template_overlay_scan_v1_lib import (
        load_tenant_overlay_doc,
        tenant_overlay_terms,
    )

    shard = {"must_keep_hard_terms": ["환불", "VIP"]}
    row = {"must_keep_terms": ["프리미엄", "███"]}
    tenant_doc = load_tenant_overlay_doc("wtt-premium-cs-customer-v1")
    assert tenant_doc is not None
    snippet = "주문번호 ███ 환불 요청합니다. VIP 고객입니다."
    terms = tenant_overlay_terms(shard, row, tenant_doc=tenant_doc, wire_snippet=snippet)
    assert "███" in terms
    assert "환불" in terms
    assert "VIP" in terms
    assert "프리미엄" in terms


def test_wtt_overlay_runner_exit_zero() -> None:
    proc = subprocess.run(
        [sys.executable, str(RUNNER)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert doc["schema"] == "ko_premium_cs_wtt_template_overlay_scan_v1"
    assert doc["wire_family"] == "CS_MASK"
    assert doc["icp_synthetic_operator_excluded"] is True
    agg = doc["aggregate"]
    assert agg["full_wire_and_twin_pass"] is True
    assert agg["exact_restore_rate_on_matched"] == 1.0
    assert agg["tenant_overlay_rate_on_matched"] == 1.0
    assert agg["snippet_candidates_total"] >= 20
