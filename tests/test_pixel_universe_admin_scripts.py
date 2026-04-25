# -*- coding: utf-8 -*-
"""Smoke/contract tests for Pixel Universe admin helper scripts."""

from __future__ import annotations

from pathlib import Path
import sys
import time

_ROOT = Path(__file__).resolve().parents[1]
_API_SERVICES = _ROOT / "api-services"
if str(_API_SERVICES) not in sys.path:
    sys.path.append(str(_API_SERVICES))

from routers.pixel_universe.router import _verify_admin_hmac
from scripts.generate_pixel_universe_admin_auth import _build_header
from scripts.run_pixel_universe_admin_ops import Config, run


def test_generate_admin_auth_header_shape() -> None:
    header = _build_header(
        role="risk_admin",
        kid="risk-v1",
        secret="dev-risk-secret-v1",
        ts=1_777_106_000,
    )
    parts = header.split(":")
    assert len(parts) == 3
    assert parts[0] == "risk-v1"
    assert parts[1] == "1777106000"
    assert len(parts[2]) == 64


def test_admin_ops_dry_run_unsuspend() -> None:
    cfg = Config(
        base_url="http://127.0.0.1:8000",
        action="unsuspend",
        agent_id="usr_ai_demo",
        kid="risk-v1",
        secret="dev-risk-secret-v1",
        timeout_sec=2.0,
        dry_run=True,
    )
    assert run(cfg) == 0


def test_admin_ops_dry_run_rotate_audit() -> None:
    cfg = Config(
        base_url="http://127.0.0.1:8000",
        action="rotate-audit",
        agent_id=None,
        kid="ops-v1",
        secret="dev-ops-secret-v1",
        timeout_sec=2.0,
        dry_run=True,
    )
    assert run(cfg) == 0


def test_generated_header_matches_router_hmac_verifier() -> None:
    ts = int(time.time())
    header = _build_header(
        role="risk_admin",
        kid="risk-v1",
        secret="dev-risk-secret-v1",
        ts=ts,
    )
    assert _verify_admin_hmac(header, "risk_admin") is True


def test_generated_header_rejected_for_wrong_role() -> None:
    ts = int(time.time())
    header = _build_header(
        role="risk_admin",
        kid="risk-v1",
        secret="dev-risk-secret-v1",
        ts=ts,
    )
    assert _verify_admin_hmac(header, "ops_audit_admin") is False
