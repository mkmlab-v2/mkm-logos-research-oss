"""Recurrence guard messages for CF token role triage (no network)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from check_cloudflare_token_roles_v1 import (  # noqa: E402
    RECURRENCE_GUARD_VERSION,
    _build_jema_ai_redirect_guard,
    _build_recurrence_guard,
)


def test_scope_mismatch_not_expired_message():
    g = _build_recurrence_guard(
        rulesets_src="user_env:CLOUDFLARE_API_TOKEN",
        rulesets_fp="cfut_D...553b",
        general_fp="cfut_D...553b",
        mkmlife_fp="cfut_D...553b",
        rulesets_ready=False,
        verify_ok=True,
        rulesets_blocker="rulesets_403_code_10000",
    )
    assert g["version"] == RECURRENCE_GUARD_VERSION
    assert g["status"] == "scope_mismatch_or_missing_rulesets_key"
    assert "token_expired" in g["misdiagnosis_avoid"]
    assert "CLOUDFLARE_API_TOKEN" in " ".join(g["never_do"])


def test_jema_ai_redirect_scope_not_expired():
    g = _build_jema_ai_redirect_guard(
        redirect_src="user_env:CLOUDFLARE_RULESETS_API_TOKEN",
        redirect_fp="cfut_5...f4fb",
        jemaai_rulesets_ready=True,
        redirect_ready=False,
        verify_ok=True,
        redirect_blocker="jema_ai_redirect_403_code_10000",
    )
    assert g["status"] == "jemaai_ok_jema_ai_zone_missing"
    assert "token_expired" in g["misdiagnosis_avoid"]
    assert "jema-ai.com" in " ".join(g["never_do"])


def test_ok_no_new_token_nag():
    g = _build_recurrence_guard(
        rulesets_src="user_env:CLOUDFLARE_RULESETS_API_TOKEN",
        rulesets_fp="cfut_X...aaaa",
        general_fp="cfut_D...553b",
        mkmlife_fp="cfut_D...553b",
        rulesets_ready=True,
        verify_ok=True,
        rulesets_blocker="rulesets_ok",
    )
    assert g["status"] == "ok"
    assert "금지" in g["agent_instruction_ko"] or "안내 금지" in g["agent_instruction_ko"]
