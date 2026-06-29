#!/usr/bin/env python3
"""Governed Reddit agent entry — Fact-Lock R1–R6 [HYPO · B-track]."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.reddit_agent_governance_lib_v1 import (  # noqa: E402
    DEFAULT_ARTIFACT,
    RedditGovernanceError,
    base_report_v1,
    count_reddit_submit_tabs,
    enforce_send_gate_for_live,
    enforce_submit_tab_invariant_v1,
    finalize_exit,
    rel,
    snapshot_before_dom_v1,
    write_artifact_v1,
)

CDP_URL = "http://127.0.0.1:9222"
OPENCHROME = ROOT / "scripts/post_bible_topology_community_openchrome_v1.py"
PRAW = ROOT / "scripts/post_reddit_praw_v1.py"


def _run_py(script: Path, args: list[str]) -> dict[str, Any]:
    cmd = [sys.executable, str(script), *args]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    tail = (proc.stdout or proc.stderr or "").strip().splitlines()
    last = tail[-1] if tail else ""
    step: dict[str, Any] = {"cmd": cmd, "exit_code": proc.returncode, "tail": last}
    try:
        step["summary"] = json.loads(last)
    except Exception:
        if proc.stderr:
            step["stderr_tail"] = proc.stderr.strip()[-500:]
    step["ok"] = proc.returncode == 0
    return step


def preflight_cdp_v1() -> dict[str, Any]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RedditGovernanceError("playwright_missing", str(exc)) from exc

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(CDP_URL)
        context = browser.contexts[0] if browser.contexts else browser.new_context()
        pages = list(context.pages)
        inv = enforce_submit_tab_invariant_v1(pages, cleanup_fn=None)
        snap = None
        if pages:
            snap = snapshot_before_dom_v1(pages[0], label="preflight")
        return {
            "cdp_url": CDP_URL,
            "page_count": len(pages),
            "submit_tab_invariant": inv,
            "snapshot": snap,
        }


def cleanup_cdp_v1() -> dict[str, Any]:
    step = _run_py(OPENCHROME, ["--cleanup-only"])
    if not step["ok"]:
        raise RedditGovernanceError("cleanup_failed", step.get("stderr_tail") or step.get("tail"))
    with __import__("playwright.sync_api", fromlist=["sync_playwright"]).sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(CDP_URL)
        context = browser.contexts[0] if browser.contexts else browser.new_context()
        inv = enforce_submit_tab_invariant_v1(list(context.pages), cleanup_fn=None)
    return {"cleanup_step": step.get("summary"), "submit_tab_invariant": inv}


def run_governed_v1(
    *,
    action: str,
    pack: str | None,
    via: str,
    dry_run: bool,
    acknowledge_send: bool,
    reddit_only: bool,
    cleanup_first: bool,
) -> dict[str, Any]:
    report = base_report_v1(action=action)
    report["pack"] = pack
    report["via"] = via
    report["dry_run"] = dry_run
    report["acknowledge_send"] = acknowledge_send

    try:
        if action == "preflight":
            report["preflight"] = preflight_cdp_v1()
            report["ok"] = True
            return report

        if action == "cleanup":
            report["cleanup"] = cleanup_cdp_v1()
            report["ok"] = True
            return report

        if action != "post":
            raise RedditGovernanceError("unknown_action", action)

        live_post = not dry_run
        enforce_send_gate_for_live(live_post=live_post, acknowledge_send=acknowledge_send)

        if via == "praw":
            if not pack:
                raise RedditGovernanceError("pack_required", "use --pack for praw")
            args = ["--pack", pack]
            if dry_run:
                args.append("--dry-run")
            if live_post:
                args.append("--acknowledge-send")
            step = _run_py(PRAW, args)
            report["steps"] = [step]
            report["ok"] = step["ok"]
            return report

        if via == "browser":
            if live_post:
                raise RedditGovernanceError(
                    "browser_live_blocked",
                    "use --via praw for live post; browser is prefill/dry-run only",
                )
            if cleanup_first:
                report["cleanup"] = cleanup_cdp_v1()
            args_oc = ["--dry-run"]
            if reddit_only:
                args_oc.append("--reddit-only")
            step = _run_py(OPENCHROME, args_oc)
            report["steps"] = [step]
            report["ok"] = step["ok"]
            return report

        raise RedditGovernanceError("unknown_via", via)

    except RedditGovernanceError as exc:
        report["ok"] = False
        report["error"] = exc.code
        report["error_detail"] = exc.detail
        return report


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("action", choices=("preflight", "cleanup", "post"))
    ap.add_argument("--pack", choices=("bible_topology", "universal_root"))
    ap.add_argument("--via", choices=("praw", "browser"), default="praw")
    ap.add_argument("--dry-run", action="store_true", help="default safe; no live submit")
    ap.add_argument("--acknowledge-send", action="store_true", help="R4 commander ack for live post")
    ap.add_argument("--reddit-only", action="store_true")
    ap.add_argument("--cleanup-first", action="store_true")
    ap.add_argument("--out", type=Path, default=DEFAULT_ARTIFACT)
    args = ap.parse_args()

    if args.action == "post" and not args.dry_run and not args.acknowledge_send:
        report = base_report_v1(action="post")
        report["error"] = "send_gate_hold"
        report["error_detail"] = "pass --dry-run or --acknowledge-send"
        write_artifact_v1(report, args.out)
        print(json.dumps({"ok": False, "error": report["error"]}, ensure_ascii=False))
        return 1

    report = run_governed_v1(
        action=args.action,
        pack=args.pack,
        via=args.via,
        dry_run=args.dry_run,
        acknowledge_send=args.acknowledge_send,
        reddit_only=args.reddit_only,
        cleanup_first=args.cleanup_first,
    )
    out = args.out if args.out.is_absolute() else ROOT / args.out
    code = finalize_exit(report, out=out)
    print(json.dumps({"ok": report.get("ok"), "artifact": rel(out), "error": report.get("error")}, ensure_ascii=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
