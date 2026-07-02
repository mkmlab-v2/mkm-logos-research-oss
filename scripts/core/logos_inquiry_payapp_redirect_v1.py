"""PayApp redirect URL validation for Logos inquiry G12 staging (no live charge)."""
from __future__ import annotations

from urllib.parse import parse_qs, urlparse


def validate_payapp_redirect_url(
    url: str,
    *,
    order_id: str,
    amount: int | None = None,
    forbid_dry_run_mul_no: bool = True,
) -> dict:
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    mul_no = (qs.get("mul_no") or [""])[0]
    ordr = (qs.get("ordr_idxx") or [""])[0]
    good_mny = (qs.get("good_mny") or [""])[0]
    checks = {
        "host_ok": parsed.scheme == "https" and parsed.netloc == "api.payapp.kr",
        "path_ok": parsed.path.startswith("/oapi/pay"),
        "mul_no_present": bool(mul_no),
        "ordr_idxx_matches": ordr == order_id,
        "good_mny_present": bool(good_mny),
        "feedbackurl_present": bool((qs.get("feedbackurl") or [""])[0]),
        "return_url_present": bool((qs.get("return_url") or [""])[0]),
        "not_dry_run_mul_no": (not forbid_dry_run_mul_no) or mul_no != "dry_run_key",
    }
    if amount is not None:
        checks["good_mny_matches"] = good_mny == str(amount)
    ok = all(checks.values())
    return {"ok": ok, "checks": checks, "host": parsed.netloc, "path": parsed.path}
