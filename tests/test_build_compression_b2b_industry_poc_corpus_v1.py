"""B2B industry PoC corpus builder + bundle smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_build_industry_corpora_ten_rows_each(tmp_path: Path) -> None:
    from scripts.build_compression_b2b_industry_poc_corpus_v1 import build_all

    paths = build_all(tmp_path)
    assert len(paths) == 4
    for p in paths:
        lines = [ln for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
        assert len(lines) == 10
        row = json.loads(lines[0])
        assert row["public_safe"] is True
        assert row["forbidden_as_customer_sla"] is True
        assert row["research_only"] is True


@pytest.mark.parametrize("external_sku", ["MKM-SCM-A1", "MKM-FIN-E1"])
def test_bundle_single_sku_smoke(external_sku: str, tmp_path: Path) -> None:
    summary = tmp_path / "bundle.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_compression_b2b_sku_industry_poc_bundle_v1.py"),
            "--sku",
            external_sku,
            "--out-summary",
            str(summary),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(summary.read_text(encoding="utf-8"))
    assert doc["bundle_ok"] is True
    assert len(doc["steps"]) == 1
    assert doc["steps"][0]["external_sku"] == external_sku
    assert doc["steps"][0]["sample_router_shard_id"] == doc["steps"][0]["forced_shard_id"]
