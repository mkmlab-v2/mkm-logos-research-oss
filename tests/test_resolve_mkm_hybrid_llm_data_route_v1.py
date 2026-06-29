# -*- coding: utf-8 -*-
"""Smoke: MKM hybrid LLM data router policy lookup (DC × MR)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/resolve_mkm_hybrid_llm_data_route_v1.py"
POLICY = ROOT / "docs/final/artifacts/mkm_hybrid_llm_data_router_v1_latest.json"

from scripts.resolve_mkm_hybrid_llm_data_route_v1 import (  # noqa: E402
    allowed_routes,
    infer_data_class,
    is_route_allowed,
    load_policy,
    resolve_route,
)


def test_policy_file_exists() -> None:
    data = load_policy(POLICY)
    assert data["schema"] == "mkm_hybrid_llm_data_router_v1"
    assert data["send_gate"] == "HOLD"
    assert len(data.get("routing_matrix") or []) == 4


@pytest.mark.parametrize(
    "data_class",
    ["DC-PUBLIC", "DC-INTERNAL", "DC-RESTRICTED", "DC-SOVEREIGN"],
)
def test_matrix_has_allowed_routes(data_class: str) -> None:
    routes = allowed_routes(data_class)
    assert routes
    assert routes[0].startswith("MR-")


def test_sovereign_forbids_saas() -> None:
    assert is_route_allowed("DC-SOVEREIGN", "MR-LOCAL-SLM") is True
    assert is_route_allowed("DC-SOVEREIGN", "MR-SAAS-FRONTIER") is False


def test_restricted_forbids_saas() -> None:
    assert is_route_allowed("DC-RESTRICTED", "MR-LOCAL-LORA") is True
    assert is_route_allowed("DC-RESTRICTED", "MR-SAAS-FRONTIER") is False


def test_public_allows_saas() -> None:
    assert is_route_allowed("DC-PUBLIC", "MR-SAAS-FRONTIER") is True


def test_path_hint_inference() -> None:
    assert infer_data_class("reports/demo/gwangmyeong_baekje_b2b_static_hub_v1.html") == "DC-PUBLIC"
    assert infer_data_class("data/compression/stateless_poc_prospect_x_v1.jsonl") == "DC-RESTRICTED"
    assert infer_data_class(".env") == "DC-SOVEREIGN"
    assert infer_data_class("unknown/blob.bin") == "DC-RESTRICTED"


def test_resolve_rejects_illegal_route() -> None:
    with pytest.raises(ValueError, match="not allowed"):
        resolve_route("DC-SOVEREIGN", requested_route="MR-SAAS-FRONTIER")


def test_cli_exit_zero(tmp_path: Path) -> None:
    out = tmp_path / "route.json"
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--data-class", "DC-RESTRICTED", "--out", str(out)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["ok"] is True
    assert data["resolution"]["route"] == "MR-LOCAL-SLM"
