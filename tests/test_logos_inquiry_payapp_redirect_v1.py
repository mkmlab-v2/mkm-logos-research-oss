"""Tests for PayApp redirect URL validator (G12 staging)."""
from __future__ import annotations

from scripts.core.logos_inquiry_payapp_redirect_v1 import validate_payapp_redirect_url


def test_valid_redirect() -> None:
    order = "mkm_test_123"
    url = (
        "https://api.payapp.kr/oapi/pay?mul_no=REALKEY&ordr_idxx=mkm_test_123"
        "&good_name=Logos&good_mny=39000"
        "&feedbackurl=https%3A%2F%2Flogos.jema-ai.com%2Fapi%2Fpayment%2Fpayapp%2Ffeedback"
        "&return_url=https%3A%2F%2Flogos.jema-ai.com%2Flogos-research%2Fask%3Fpaid%3D1"
    )
    report = validate_payapp_redirect_url(url, order_id=order, amount=39000)
    assert report["ok"] is True


def test_rejects_dry_run_mul_no() -> None:
    order = "mkm_test_456"
    url = (
        "https://api.payapp.kr/oapi/pay?mul_no=dry_run_key&ordr_idxx=mkm_test_456"
        "&good_mny=39000&feedbackurl=x&return_url=y"
    )
    report = validate_payapp_redirect_url(url, order_id=order, amount=39000)
    assert report["ok"] is False
    assert report["checks"]["not_dry_run_mul_no"] is False
