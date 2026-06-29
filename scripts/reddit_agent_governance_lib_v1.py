#!/usr/bin/env python3
"""Reddit community agent Fact-Lock governance R1–R6 [HYPO · B-track]."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]

SEND_GATE_DEFAULT = "HOLD"
MAX_SUBMIT_TABS = 1
DEFAULT_ARTIFACT = ROOT / "reports/reddit_agent_run_v1_latest.json"
GOVERNANCE_RULES = ("R1_submit_tab", "R2_snapshot", "R3_tier3_human", "R4_send_gate", "R5_artifact", "R6_btrack")


class RedditGovernanceError(RuntimeError):
    def __init__(self, code: str, detail: str | None = None) -> None:
        self.code = code
        self.detail = detail
        msg = code if not detail else f"{code}:{detail}"
        super().__init__(msg)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def base_report_v1(*, action: str) -> dict[str, Any]:
    return {
        "schema": "reddit_agent_run_v1",
        "research_only": True,
        "send_gate": SEND_GATE_DEFAULT,
        "hypothesis_class": "HYPO",
        "track": "B-track",
        "generated_at_utc": utc_now(),
        "action": action,
        "governance_rules": list(GOVERNANCE_RULES),
        "ok": False,
    }


def enforce_send_gate_for_live(*, live_post: bool, acknowledge_send: bool) -> None:
    """R4: default HOLD — live submit requires explicit commander ack."""
    if live_post and not acknowledge_send:
        raise RedditGovernanceError("send_gate_hold", "pass --acknowledge-send for live post")


def count_reddit_submit_tabs(pages: list[Any]) -> int:
    n = 0
    for page in pages:
        url = (getattr(page, "url", None) or "").lower()
        if "reddit.com" in url and "/submit" in url:
            n += 1
    return n


def enforce_submit_tab_invariant_v1(
    pages: list[Any],
    *,
    cleanup_fn: Callable[[], int] | None = None,
) -> dict[str, Any]:
    """R1: at most one reddit /submit tab; no retry loop on violation."""
    before = count_reddit_submit_tabs(pages)
    closed = 0
    after = before
    if before > MAX_SUBMIT_TABS and cleanup_fn is not None:
        closed = int(cleanup_fn())
        after = count_reddit_submit_tabs(pages)
    if after > MAX_SUBMIT_TABS:
        raise RedditGovernanceError(
            "submit_tab_invariant_violation",
            f"count={after} max={MAX_SUBMIT_TABS}",
        )
    return {"submit_tabs_before": before, "submit_tabs_after": after, "stale_tabs_closed": closed}


def check_tier3_human_gate_v1(*, url: str, captcha_visible: bool = False) -> None:
    """R3: login/CAPTCHA/post UI = commander Chrome; agent must stop."""
    low = (url or "").lower()
    if "/login" in low or "login.reddit.com" in low:
        raise RedditGovernanceError("tier3_login_required", url)
    if captcha_visible:
        raise RedditGovernanceError("tier3_captcha_human_required")


def snapshot_before_dom_v1(page: Any, *, label: str, out_dir: Path | None = None) -> dict[str, Any]:
    """R2: capture URL/title/screenshot before DOM mutation."""
    out_base = out_dir or (ROOT / "reports")
    out_base.mkdir(parents=True, exist_ok=True)
    shot = out_base / f"reddit_agent_snapshot_{label}_v1.png"
    try:
        page.screenshot(path=str(shot), full_page=False)
        shot_rel = rel(shot)
    except Exception as exc:  # noqa: BLE001
        shot_rel = None
        return {
            "ok": False,
            "label": label,
            "url": getattr(page, "url", None),
            "title": None,
            "screenshot": shot_rel,
            "error": f"snapshot_failed:{exc}",
        }
    try:
        title = page.title()
    except Exception:
        title = None
    return {
        "ok": True,
        "label": label,
        "url": getattr(page, "url", None),
        "title": title,
        "screenshot": shot_rel,
    }


def write_artifact_v1(report: dict[str, Any], out: Path | None = None) -> Path:
    """R5: every run ends with JSON artifact."""
    path = out or DEFAULT_ARTIFACT
    if not path.is_absolute():
        path = ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def finalize_exit(report: dict[str, Any], *, out: Path | None = None) -> int:
    path = write_artifact_v1(report, out)
    report["artifact"] = rel(path)
    return 0 if report.get("ok") else 1
