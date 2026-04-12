# @MKM12-METADATA
# Type: Logic
# Purpose: Staging log shard builder (heuristic path) matches codebook shard schema.
from __future__ import annotations

import json
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_CONFIG = _ROOT / "docs" / "final" / "artifacts" / "inference_config_v1.json"


@pytest.mark.skipif(not _CONFIG.is_file(), reason="inference_config_v1.json missing")
def test_build_staging_shard_heuristic_schema() -> None:
    from scripts.staging_shard_inference_run import _load_json, build_staging_shard

    cfg = _load_json(_CONFIG)
    shard = build_staging_shard(
        cfg,
        use_llm=False,
        sample_path=None,
        gemini_model="gemini-2.5-flash",
        timeout_s=30,
    )
    required = {
        "shard_id",
        "domain",
        "routing_keywords",
        "must_keep_hard_terms",
        "must_keep_soft_terms",
        "guard_tokens",
        "hangul_principle",
    }
    assert required.issubset(shard.keys())
    assert shard["shard_id"] == cfg.get("target_shard_id")
    assert "timestamp" in [x.lower() for x in shard["must_keep_hard_terms"]]


def test_dedupe_lower() -> None:
    from scripts.staging_shard_inference_run import _dedupe_lower

    assert _dedupe_lower(["A", "a", "b"]) == ["a", "b"]
