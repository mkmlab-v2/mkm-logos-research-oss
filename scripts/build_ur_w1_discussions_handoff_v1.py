#!/usr/bin/env python3
"""Build UR-W1 Discussions handoff JSON — human paste paths + gate status (research_only)."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/universal_root_w1_discussions_handoff_v1_latest.json"
GTM = ROOT / "reports/universal_root_community_gtm_v1_latest.json"
POLL = ROOT / "reports/universal_root_community_poll_v1_latest.json"
WEEKLY = ROOT / "reports/universal_root_community_gtm_weekly_v1_latest.json"
BUMP_POST = ROOT / "reports/universal_root_discussions_bump_post_v1_latest.json"
THREAD_B_POST = ROOT / "reports/universal_root_discussions_thread_b_post_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _push_mirror_sha() -> str | None:
    mirror = ROOT / "exports/_push-mkm-universal-root"
    if not (mirror / ".git").is_dir():
        return None
    proc = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=str(mirror),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return None
    return (proc.stdout or "").strip() or None


def _read(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build(
    *,
    gtm: dict[str, Any] | None,
    poll: dict[str, Any] | None,
    weekly: dict[str, Any] | None,
    bump_post: dict[str, Any] | None,
    thread_b_post: dict[str, Any] | None,
) -> dict[str, Any]:
    discussions = (gtm or {}).get("channels", {}).get("github_discussions", {})
    external_repro = int(discussions.get("external_repro_reports") or 0)
    thread_b_blocked = external_repro < 1
    thread_b_posted = (
        str(discussions.get("thread_b_status") or "") == "posted"
        or bool(thread_b_post and thread_b_post.get("ok") and thread_b_post.get("discussion_url"))
    )

    disc = (poll or {}).get("discussion") or {}
    comment_previews = " ".join(
        str(c.get("body_preview") or "") for c in (disc.get("comments") or [])
    ).lower()

    paste_files = {
        "thread_a_macos_cta": "reports/human_paste/universal_root_discussions_thread_a_macos_cta_reply.md",
        "thread_a_bump": "reports/human_paste/universal_root_discussions_thread_a_post_push_bump.md",
        "bench_5k_discussion": "reports/human_paste/universal_root_discussions_bench_5k_v1.md",
        "thread_b_title": "reports/human_paste/universal_root_discussions_thread_b_title.txt",
        "thread_b_body": "reports/human_paste/universal_root_discussions_thread_b_body.md",
        "smoke_evidence_png": "reports/human_paste/universal_root_smoke_terminal_evidence.png",
    }
    missing = [k for k, rel in paste_files.items() if not (ROOT / rel).is_file()]

    bench_5k_posted = bool(
        bump_post
        and bump_post.get("ok")
        and "bench_5k" in str(bump_post.get("body_file") or "")
    )
    bench_5k_comment_url = bump_post.get("html_url") if bench_5k_posted else None

    macos_cta_posted = bool(
        bump_post
        and bump_post.get("ok")
        and "macos_cta" in str(bump_post.get("body_file") or "")
    ) or (
        "awaiting community repro" in comment_previews
        or ("macos" in comment_previews and "cross-platform status" in comment_previews)
    )
    macos_cta_url = (
        bump_post.get("html_url")
        if bump_post and bump_post.get("ok") and bump_post.get("html_url") and macos_cta_posted
        else None
    )
    if thread_b_posted:
        recommended_next = "community_poll_weekly"
    elif bench_5k_posted and not thread_b_blocked:
        recommended_next = "thread_b_after_external_repro"
    elif thread_b_blocked:
        recommended_next = (
            "await_external_macos_repro" if macos_cta_posted else "thread_a_macos_cta"
        )
    else:
        recommended_next = "bench_5k_discussion_comment"

    if thread_b_posted:
        thread_b_action = "posted"
    elif thread_b_blocked:
        thread_b_action = "blocked_await_external_repro"
    else:
        thread_b_action = "eligible_for_auto_post"

    return {
        "schema": "universal_root_w1_discussions_handoff_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "discussion_url": discussions.get("thread_a_url"),
        "external_repro_reports": external_repro,
        "thread_b_action": thread_b_action,
        "thread_b_url": discussions.get("thread_b_url") or (
            thread_b_post.get("discussion_url") if thread_b_post else None
        ),
        "bench_5k_posted": bench_5k_posted,
        "bench_5k_comment_url": bench_5k_comment_url,
        "github_export_push_sha": _push_mirror_sha(),
        "macos_cta_posted": macos_cta_posted,
        "macos_cta_comment_url": macos_cta_url,
        "poll_summary": {
            "last_poll_utc": poll.get("generated_at_utc") if poll else None,
            "comment_count": disc.get("comment_count") if disc else discussions.get("comment_count"),
        },
        "weekly_summary": {
            "last_run_utc": weekly.get("generated_at_utc") if weekly else None,
            "ok": weekly.get("ok") if weekly else None,
        },
        "human_paste_tier3": {
            "policy": "commander_browser_only",
            "recommended_next": recommended_next,
            "files": paste_files,
            "missing_files": missing,
        },
        "automatable_next": [
            "py scripts/poll_universal_root_community_gtm_v1.py",
            "powershell -File scripts/Invoke-UniversalRootCommunityGtmWeeklyRoutine_v1.ps1",
        ]
        + (
            []
            if thread_b_blocked or thread_b_posted
            else ["py scripts/post_universal_root_discussions_thread_b_v1.py --dry-run"]
        ),
        "forbidden_claims": [
            "UR-W1 complete without external_repro >= 1",
            "Track A promotion from community GTM alone",
        ],
        "reproduce": "py scripts/build_ur_w1_discussions_handoff_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    doc = build(
        gtm=_read(GTM),
        poll=_read(POLL),
        weekly=_read(WEEKLY),
        bump_post=_read(BUMP_POST),
        thread_b_post=_read(THREAD_B_POST),
    )
    if doc.get("macos_cta_posted") and GTM.is_file():
        gtm_doc = _read(GTM) or {}
        gh = gtm_doc.setdefault("channels", {}).setdefault("github_discussions", {})
        gh["macos_cta_posted"] = True
        gh["macos_cta_comment_url"] = doc.get("macos_cta_comment_url")
        gh["macos_cta_posted_utc"] = (bump_post := _read(BUMP_POST)) and bump_post.get("generated_at_utc")
        GTM.write_text(json.dumps(gtm_doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.out).replace("\\", "/"), "thread_b_action": doc["thread_b_action"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
