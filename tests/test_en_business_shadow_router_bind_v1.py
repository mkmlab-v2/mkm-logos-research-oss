"""[HYPO] En business shadow router bind — B-track sandbox."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/run_en_business_shadow_router_bind_v1.py"
ARTIFACT = ROOT / "docs/final/artifacts/en_business_shadow_router_bind_v1_latest.json"
BIND_SPEC = ROOT / "docs/final/artifacts/compression_en_business_shadow_router_bind_v1.json"
SHARDS = ROOT / "codebook/shards"


def test_shadow_bind_spec_schema() -> None:
    doc = json.loads(BIND_SPEC.read_text(encoding="utf-8"))
    assert doc["schema"] == "compression_en_business_shadow_router_bind_v1"
    assert doc["shadow_only"] is True
    assert doc["production_router_unchanged"] is True
    assert doc["shadow_shard_id"] == "zone_h_en_business_v1"
    assert "en_biz_v1" in doc["corpus_tag_aliases"]


def test_shadow_bind_lib_forces_shard_on_tag() -> None:
    from scripts.core.domain_router import DomainSpecificRouter
    from scripts.en_business_shadow_router_bind_v1_lib import (
        compare_baseline_vs_shadow,
        load_shadow_bind_spec,
        resolve_shadow_shard_id,
    )

    spec = load_shadow_bind_spec(BIND_SPEC)
    assert resolve_shadow_shard_id("en_biz_v1", spec) == "zone_h_en_business_v1"
    router = DomainSpecificRouter(SHARDS)
    cmp = compare_baseline_vs_shadow(
        "risk drawdown leverage control invoice payment",
        corpus_tag="en_biz_v1",
        router=router,
        spec=spec,
    )
    assert cmp["shadow_applied"] is True
    assert cmp["shadow_route"]["shard_id"] == "zone_h_en_business_v1"
    assert cmp["baseline_route"]["shard_id"] == "zone_e_finance"
    assert cmp["diverges_from_baseline"] is True


def test_shadow_bind_no_apply_without_tag() -> None:
    from scripts.core.domain_router import DomainSpecificRouter
    from scripts.en_business_shadow_router_bind_v1_lib import (
        compare_baseline_vs_shadow,
        load_shadow_bind_spec,
    )

    spec = load_shadow_bind_spec(BIND_SPEC)
    router = DomainSpecificRouter(SHARDS)
    cmp = compare_baseline_vs_shadow(
        "invoice payment contract",
        corpus_tag=None,
        router=router,
        spec=spec,
    )
    assert cmp["shadow_applied"] is False
    assert cmp["diverges_from_baseline"] is False


def test_shadow_bind_runner_exit_zero() -> None:
    proc = subprocess.run(
        [sys.executable, str(RUNNER)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert doc["schema"] == "en_business_shadow_router_bind_eval_v1"
    assert doc["shadow_only"] is True
    agg = doc["aggregate"]
    assert agg["full_shadow_bind_pass"] is True
    assert agg["shadow_applied_count"] >= 13
    assert doc["shadow_shard_id"] == "zone_h_en_business_v1"
