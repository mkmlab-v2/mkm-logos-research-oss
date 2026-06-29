#!/usr/bin/env python3
"""CDP session guard — reuse giryun288 portal tab; never spawn OAuth loops."""
from __future__ import annotations

from typing import Any

GIRYUN_MARKERS = (
    "giryun288gmail",
    "giryun288@gmail.com",
    "mkm-startups-prod",
)
WRONG_MARKERS = (
    "moksorinwgmail",
    "moksorinw@gmail.com",
)
LOGIN_URL_FRAGMENTS = (
    "login.microsoftonline.com",
    "login.live.com",
    "github.com/login",
    "portal.startups.microsoft.com/login",
)


def _body(page) -> str:
    parts: list[str] = []
    try:
        parts.append(page.inner_text("body", timeout=10_000) or "")
    except Exception:
        pass
    for fr in page.frames:
        try:
            t = fr.inner_text("body", timeout=2000) or ""
            if len(t) > 80:
                parts.append(t)
        except Exception:
            continue
    return "\n".join(parts)


def is_login_url(url: str) -> bool:
    u = (url or "").lower()
    return any(x in u for x in LOGIN_URL_FRAGMENTS)


def is_giryun288_session(text: str) -> bool:
    low = text.lower()
    if any(w in low for w in WRONG_MARKERS):
        return False
    return any(m in low for m in GIRYUN_MARKERS)


def find_giryun288_portal(browser):
    """Return portal tab already on giryun288 tenant, or None."""
    best = None
    for ctx in browser.contexts:
        for pg in ctx.pages:
            url = pg.url or ""
            if "portal.azure.com" not in url or is_login_url(url):
                continue
            if "error=invalid_request" in url or "AADSTS" in url:
                continue
            try:
                text = _body(pg)
            except Exception:
                continue
            if is_giryun288_session(text):
                return pg
            if best is None and "portal.azure.com" in url:
                best = pg
    return best


def refuse_login_navigation(run: dict[str, Any], reason: str) -> dict[str, Any]:
    run["login_loop_prevented"] = True
    run["human_gate"] = "stop_script_use_existing_portal_tab"
    run["hint"] = (
        "CDP(9222)에서 login/github/startups/login 탭을 닫고, "
        "portal.azure.com/#@giryun288gmail... 구독 overview 탭 하나만 연 채 "
        "readonly probe만 실행. 스크립트가 new_page/OAuth를 다시 열면 무한 로그인."
    )
    run["reason"] = reason
    return run
