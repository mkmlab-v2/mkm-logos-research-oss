#!/usr/bin/env python3
"""Post Bible topology GTM to Reddit r/LocalLLM + X via openchrome CDP (Tier 3 · commander Chrome).

DEPRECATED for live Reddit submit — use scripts/post_reddit_praw_v1.py (official API).
This script: prefill form, dry-run, tab cleanup, X compose assist only.

Prereq: Chrome with --remote-debugging-port=9222 logged into Reddit + X.
Paste SSOT: reports/human_paste/bible_topology_reddit_* · bible_topology_x_post_1.txt
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.reddit_agent_governance_lib_v1 import (  # noqa: E402
    RedditGovernanceError,
    check_tier3_human_gate_v1,
    enforce_send_gate_for_live,
    enforce_submit_tab_invariant_v1,
    snapshot_before_dom_v1,
)

CDP_URL = "http://127.0.0.1:9222"
OUT = ROOT / "reports/bible_topology_community_auto_post_v1_latest.json"
REDDIT_TITLE = ROOT / "reports/human_paste/bible_topology_reddit_title.txt"
REDDIT_BODY = ROOT / "reports/human_paste/bible_topology_reddit_body.md"
X_BODY = ROOT / "reports/human_paste/bible_topology_x_post_1.txt"
REDDIT_SUBMIT = "https://old.reddit.com/r/LocalLLM/submit"
REDDIT_SUBMIT_NEW = "https://www.reddit.com/r/LocalLLM/submit/?type=TEXT"
X_COMPOSE = "https://x.com/compose/post"

# X hard limit — shorten if paste file exceeds
X_FALLBACK = (
    "Sibling OSS to mkm-universal-root: bible topology contributor shards "
    "(Tier A passion seed, CI lint). Not a 63k dump.\n\n"
    "https://github.com/mkmlab-v2/mkm-bible-topology-crosswalk\n"
    "research_only · send_gate HOLD"
)


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig").strip()


def _reddit_body_plain(md: str) -> str:
    # Reddit accepts markdown; strip code fence language only
    return md.replace("\r\n", "\n")


def _x_text(raw: str) -> str:
    text = raw.strip()
    if len(text) <= 280:
        return text
    return X_FALLBACK


def _reddit_captcha_visible(page) -> bool:
    return page.locator('iframe[src*="recaptcha"]:visible').count() > 0


def _reddit_post_success(url: str) -> bool:
    low = url.lower()
    return "/comments/" in low and "/submit" not in low


def _reddit_flair_modal_open(page) -> bool:
    return page.locator("#post-flair-modal-apply-button").count() > 0


def _reddit_close_flair_modal(page) -> None:
    """Dismiss flair modal so we never leave the browser stuck (Cancel fallback)."""
    if not _reddit_flair_modal_open(page):
        return
    try:
        page.locator("#post-flair-modal-apply-button").click(timeout=3000)
        page.wait_for_timeout(800)
        return
    except Exception:
        pass
    try:
        page.locator('button:has-text("Cancel")').click(timeout=3000)
        page.wait_for_timeout(500)
    except Exception:
        pass


def _reddit_pick_flair(page) -> bool:
    if page.locator("text=Your post must contain post flair").count() == 0:
        return True
    try:
        if not _reddit_flair_modal_open(page):
            page.locator('button:has-text("Add flair")').first.click(timeout=8000)
            page.wait_for_timeout(1500)
        if not _reddit_flair_modal_open(page):
            return page.locator("text=Your post must contain post flair").count() == 0
        try:
            page.locator('faceplate-radio-input[name="flairId"]').nth(1).click(force=True, timeout=4000)
        except Exception:
            try:
                page.get_by_text("Discussion", exact=True).click(force=True, timeout=4000)
            except Exception:
                pass
        page.wait_for_timeout(400)
        page.locator("#post-flair-modal-apply-button").click(timeout=8000)
        page.wait_for_timeout(1500)
        if _reddit_flair_modal_open(page):
            raise RuntimeError("flair_modal_still_open_after_add")
        return page.locator("text=Your post must contain post flair").count() == 0
    except Exception as exc:
        raise RuntimeError(f"flair_pick_failed:{exc}") from exc


def _acquire_work_page(context, *, prefer_url_part: str = "reddit.com"):
    """Reuse one Reddit tab when possible — avoid opening a new tab every run."""
    for page in context.pages:
        url = page.url or ""
        if prefer_url_part in url and "/submit" in url:
            return page, False
    for page in context.pages:
        url = page.url or ""
        if prefer_url_part in url:
            return page, False
    if context.pages:
        return context.pages[0], False
    return context.new_page(), True


def _close_stale_reddit_submit_tabs(context, keep_page) -> int:
    closed = 0
    for page in list(context.pages):
        if page is keep_page:
            continue
        url = page.url or ""
        if "reddit.com" in url and "/submit" in url:
            try:
                _reddit_close_flair_modal(page)
                page.close()
                closed += 1
            except Exception:
                pass
    return closed


def _reddit_type_field(page, locator, text: str) -> None:
    locator.wait_for(state="visible", timeout=30000)
    locator.click()
    page.keyboard.press("Control+A")
    page.keyboard.type(text, delay=5)


def _reddit_set_lexical_body(page, body: str) -> None:
    clicked = False
    for sel in (
        "reddit-rte",
        "shreddit-post-text-body",
        '[slot="text-body"]',
        'div[aria-label="Post body"]',
    ):
        loc = page.locator(sel).first
        if loc.count() > 0:
            try:
                loc.click(timeout=5000)
                clicked = True
                break
            except Exception:
                continue
    if not clicked:
        page.get_by_text("Body text", exact=False).first.click(timeout=5000)
    page.wait_for_timeout(400)
    page.keyboard.press("Control+A")
    page.keyboard.type(body, delay=2)


def post_reddit_new_ui(page, *, title: str, body: str, dry_run: bool) -> dict:
    step: dict = {"platform": "reddit", "subreddit": "LocalLLM", "ok": False, "ui": "new_reddit_text"}
    try:
        step["snapshot_before"] = snapshot_before_dom_v1(page, label="reddit_new_pre_nav")
        page.goto(REDDIT_SUBMIT_NEW, wait_until="domcontentloaded", timeout=90000)
        page.wait_for_timeout(5000)
        step["final_url"] = page.url
        check_tier3_human_gate_v1(url=page.url, captcha_visible=_reddit_captcha_visible(page))
        if "/login" in page.url.lower():
            step["error"] = "redirected_to_login"
            return step

        title_input = page.locator(
            '[name="title"], input[placeholder*="Title"], textarea[placeholder*="Title"]'
        ).first
        _reddit_type_field(page, title_input, title)
        page.wait_for_timeout(800)
        _reddit_set_lexical_body(page, body)
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(500)
        title_input = page.locator('[name="title"]').first
        _reddit_type_field(page, title_input, title)

        step["title_len"] = len(title)
        step["body_len"] = len(body)
        try:
            _reddit_pick_flair(page)
        except RuntimeError as exc:
            step["error"] = str(exc)
            step["status"] = "blocked_flair"
            page.screenshot(path=str(ROOT / "reports/bible_topology_reddit_error_v1.png"), full_page=False)
            step["error_screenshot"] = "reports/bible_topology_reddit_error_v1.png"
            return step
        page.wait_for_timeout(800)
        if page.locator("text=Your post must contain post flair").count() > 0:
            try:
                _reddit_pick_flair(page)
            except RuntimeError as exc:
                step["error"] = str(exc)
                step["status"] = "blocked_flair"
                return step
        page.screenshot(path=str(ROOT / "reports/bible_topology_reddit_preflight_v1.png"), full_page=False)
        step["screenshot"] = "reports/bible_topology_reddit_preflight_v1.png"

        if dry_run:
            step["ok"] = True
            step["status"] = "dry_run"
            return step

        post_btn = page.locator('button:has-text("Post"), shreddit-post-submit-button button').first
        post_btn.wait_for(state="visible", timeout=15000)
        for _ in range(20):
            if not post_btn.is_disabled():
                break
            page.wait_for_timeout(500)
        if post_btn.is_disabled():
            step["error"] = "post_button_disabled"
            step["status"] = "blocked_ui"
            return step
        post_btn.click()
        page.wait_for_timeout(3000)
        if page.locator('[role="dialog"]').filter(has_text="flair").count() > 0 or _reddit_flair_modal_open(page):
            try:
                _reddit_pick_flair(page)
            except RuntimeError:
                _reddit_close_flair_modal(page)
                step["error"] = "flair_required_after_post_click"
                step["status"] = "blocked_flair"
                return step
            post_btn = page.locator('button:has-text("Post"), shreddit-post-submit-button button').first
            for _ in range(20):
                if not post_btn.is_disabled():
                    break
                page.wait_for_timeout(500)
            if not post_btn.is_disabled():
                post_btn.click()
        page.wait_for_timeout(20000)
        step["final_url"] = page.url
        page.screenshot(path=str(ROOT / "reports/bible_topology_reddit_post_result_v1.png"), full_page=False)
        step["result_screenshot"] = "reports/bible_topology_reddit_post_result_v1.png"

        if _reddit_captcha_visible(page):
            step["error"] = "captcha_or_verify_required"
            step["status"] = "blocked_captcha"
            return step
        if _reddit_post_success(page.url):
            step["ok"] = True
            step["status"] = "posted"
            step["permalink_hint"] = page.url
        else:
            body_snip = page.inner_text("body")[:3000].lower()
            if "removed by reddit" in body_snip:
                step["ok"] = True
                step["status"] = "posted_filter_removed"
                step["note"] = "Submitted but hidden by Reddit spam filter; mod review may be needed"
            else:
                step["status"] = "uncertain"
                step["error"] = f"unexpected_url:{page.url}"
    except Exception as exc:
        step["error"] = str(exc)
        try:
            page.screenshot(path=str(ROOT / "reports/bible_topology_reddit_error_v1.png"), full_page=False)
            step["error_screenshot"] = "reports/bible_topology_reddit_error_v1.png"
        except Exception:
            pass
    return step


def post_reddit_old_ui(page, *, title: str, body: str, dry_run: bool) -> dict:
    step: dict = {"platform": "reddit", "subreddit": "LocalLLM", "ok": False, "ui": "old_reddit_text_tab"}
    try:
        page.goto(REDDIT_SUBMIT, wait_until="domcontentloaded", timeout=90000)
        page.wait_for_timeout(3000)
        step["final_url"] = page.url
        if "/login" in page.url.lower():
            step["error"] = "redirected_to_login"
            return step

        text_tab = page.locator('ul.tabmenu a', has_text="text").first
        text_tab.click()
        page.wait_for_timeout(1500)

        title_input = page.locator('textarea[name="title"], input[name="title"]').first
        title_input.wait_for(state="visible", timeout=20000)
        title_input.fill(title)

        body_area = page.locator('textarea[name="text"]').first
        body_area.wait_for(state="visible", timeout=20000)
        body_area.fill(body)

        step["title_len"] = len(title)
        step["body_len"] = len(body)
        page.screenshot(path=str(ROOT / "reports/bible_topology_reddit_preflight_v1.png"), full_page=False)
        step["screenshot"] = "reports/bible_topology_reddit_preflight_v1.png"

        if _reddit_captcha_visible(page):
            step["error"] = "captcha_or_verify_required"
            step["status"] = "blocked_captcha"
            return step

        if dry_run:
            step["ok"] = True
            step["status"] = "dry_run"
            return step

        submit_btn = page.locator('button[type="submit"], input[type="submit"]').first
        submit_btn.click()
        page.wait_for_timeout(12000)
        step["final_url"] = page.url
        page.screenshot(path=str(ROOT / "reports/bible_topology_reddit_post_result_v1.png"), full_page=False)
        step["result_screenshot"] = "reports/bible_topology_reddit_post_result_v1.png"

        if _reddit_captcha_visible(page):
            step["error"] = "captcha_or_verify_required"
            step["status"] = "blocked_captcha"
            return step
        if _reddit_post_success(page.url):
            step["ok"] = True
            step["status"] = "posted"
            step["permalink_hint"] = page.url
        else:
            step["status"] = "uncertain"
            step["error"] = f"unexpected_url:{page.url}"
    except Exception as exc:
        step["error"] = str(exc)
        try:
            page.screenshot(path=str(ROOT / "reports/bible_topology_reddit_error_v1.png"), full_page=False)
            step["error_screenshot"] = "reports/bible_topology_reddit_error_v1.png"
        except Exception:
            pass
    return step


def post_reddit(page, *, title: str, body: str, dry_run: bool) -> dict:
    return post_reddit_new_ui(page, title=title, body=body, dry_run=dry_run)


def post_x(page, *, text: str, dry_run: bool) -> dict:
    step: dict = {"platform": "x", "ok": False, "char_count": len(text)}
    try:
        page.goto(X_COMPOSE, wait_until="domcontentloaded", timeout=90000)
        page.wait_for_timeout(5000)
        step["final_url"] = page.url
        if "login" in page.url.lower() or "onboarding" in page.url.lower():
            step["error"] = "redirected_to_login"
            step["status"] = "skipped_not_logged_in"
            return step

        box = page.locator('[data-testid="tweetTextarea_0"] div[contenteditable="true"]').first
        if box.count() == 0:
            box = page.locator('div[contenteditable="true"][role="textbox"]').first
        box.wait_for(state="visible", timeout=30000)
        box.click()
        box.fill(text)

        page.screenshot(path=str(ROOT / "reports/bible_topology_x_preflight_v1.png"), full_page=False)
        step["screenshot"] = "reports/bible_topology_x_preflight_v1.png"

        if dry_run:
            step["ok"] = True
            step["status"] = "dry_run"
            return step

        post_btn = page.locator('[data-testid="tweetButton"], [data-testid="tweetButtonInline"]').first
        post_btn.wait_for(state="visible", timeout=15000)
        post_btn.click()
        page.wait_for_timeout(6000)
        step["final_url"] = page.url
        page.screenshot(path=str(ROOT / "reports/bible_topology_x_post_result_v1.png"), full_page=False)
        step["result_screenshot"] = "reports/bible_topology_x_post_result_v1.png"
        step["ok"] = True
        step["status"] = "posted_heuristic"
    except Exception as exc:
        step["error"] = str(exc)
        try:
            page.screenshot(path=str(ROOT / "reports/bible_topology_x_error_v1.png"), full_page=False)
            step["error_screenshot"] = "reports/bible_topology_x_error_v1.png"
        except Exception:
            pass
    return step


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="Fill forms only; do not click Post")
    ap.add_argument("--reddit-only", action="store_true")
    ap.add_argument("--x-only", action="store_true")
    ap.add_argument(
        "--cleanup-stale-tabs",
        action="store_true",
        help="Close extra reddit.com/.../submit tabs before run (keeps work tab)",
    )
    ap.add_argument(
        "--cleanup-only",
        action="store_true",
        help="Only close stale reddit submit tabs + dismiss flair modals; no post",
    )
    ap.add_argument(
        "--acknowledge-send",
        action="store_true",
        help="R4 commander ack for live Post click (default: dry-run / prefill only)",
    )
    args = ap.parse_args()

    try:
        enforce_send_gate_for_live(live_post=not args.dry_run, acknowledge_send=args.acknowledge_send)
    except RedditGovernanceError as exc:
        report = {
            "schema": "bible_topology_community_auto_post_v1",
            "research_only": True,
            "send_gate": "HOLD",
            "ok": False,
            "error": exc.code,
            "error_detail": exc.detail,
        }
        OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"ok": False, "error": exc.code}, ensure_ascii=False))
        return 5

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright not installed", file=sys.stderr)
        return 2

    title = _read(REDDIT_TITLE)
    body = _reddit_body_plain(_read(REDDIT_BODY))
    x_text = _x_text(_read(X_BODY))

    do_reddit = not args.x_only
    do_x = not args.reddit_only

    report: dict = {
        "schema": "bible_topology_community_auto_post_v1",
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "track": "B-track",
        "generated_at_utc": _utc(),
        "dry_run": args.dry_run,
        "acknowledge_send": args.acknowledge_send,
        "cdp_url": CDP_URL,
        "steps": [],
    }

    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp(CDP_URL)
        except Exception as exc:
            report["ok"] = False
            report["error"] = f"cdp_connect_failed: {exc}"
            OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(json.dumps(report, ensure_ascii=False))
            return 3

        context = browser.contexts[0] if browser.contexts else browser.new_context()

        def _cleanup_submit_tabs() -> int:
            page, _ = _acquire_work_page(context, prefer_url_part="reddit.com")
            return _close_stale_reddit_submit_tabs(context, keep_page=page)

        try:
            if args.cleanup_only:
                inv = enforce_submit_tab_invariant_v1(list(context.pages), cleanup_fn=_cleanup_submit_tabs)
            else:
                inv = enforce_submit_tab_invariant_v1(
                    list(context.pages),
                    cleanup_fn=_cleanup_submit_tabs if (args.cleanup_stale_tabs or do_reddit) else None,
                )
            report["submit_tab_invariant"] = inv
        except RedditGovernanceError as exc:
            report["ok"] = False
            report["error"] = exc.code
            report["error_detail"] = exc.detail
            OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(json.dumps({"ok": False, "error": exc.code}, ensure_ascii=False))
            return 1

        if args.cleanup_only:
            page, _ = _acquire_work_page(context, prefer_url_part="reddit.com")
            stale_closed = _close_stale_reddit_submit_tabs(context, keep_page=page)
            for p in context.pages:
                try:
                    _reddit_close_flair_modal(p)
                except Exception:
                    pass
            report["stale_reddit_tabs_closed"] = stale_closed
            report["ok"] = True
            report["status"] = "cleanup_only"
            OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(json.dumps({"ok": True, "stale_reddit_tabs_closed": stale_closed}, ensure_ascii=False))
            return 0

        prefer = "reddit.com" if do_reddit else "x.com"
        page, created_new = _acquire_work_page(context, prefer_url_part=prefer)
        stale_closed = 0
        if (args.cleanup_stale_tabs or do_reddit) and do_reddit:
            stale_closed = _close_stale_reddit_submit_tabs(context, keep_page=page)
        report["stale_reddit_tabs_closed"] = stale_closed
        report["page_reused"] = not created_new
        try:
            if do_reddit:
                report["steps"].append(post_reddit(page, title=title, body=body, dry_run=args.dry_run))
            if do_x:
                report["steps"].append(post_x(page, text=x_text, dry_run=args.dry_run))
        finally:
            try:
                _reddit_close_flair_modal(page)
            except Exception:
                pass
            if created_new:
                try:
                    page.close()
                except Exception:
                    pass

    report["ok"] = all(s.get("ok") for s in report["steps"]) if report["steps"] else False
    report["partial_ok"] = any(s.get("ok") for s in report["steps"])
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": report["ok"], "steps": report["steps"]}, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
