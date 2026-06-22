#!/usr/bin/env python3
"""Poll Universal Root community channels (GitHub Discussions #2) and patch GTM SSOT."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GTM = ROOT / "reports/universal_root_community_gtm_v1_latest.json"
OUT = ROOT / "reports/universal_root_community_poll_v1_latest.json"
REPO = "mkmlab-v2/mkm-universal-root"
DISCUSSION = 2
AUTHOR_LOGINS = frozenset({"mkmlab-v2", "moksorinw"})


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _gh_json(args: list[str]) -> list | dict:
    proc = subprocess.run(
        ["gh", "api", *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "gh api failed")
    return json.loads(proc.stdout or "null")


def _fetch_discussion_comments() -> list[dict]:
    data = _gh_json([f"repos/{REPO}/discussions/{DISCUSSION}/comments"])
    if not isinstance(data, list):
        return []
    rows: list[dict] = []
    for row in data:
        user = row.get("user") or {}
        login = str(user.get("login") or "")
        rows.append(
            {
                "id": row.get("id"),
                "user": login,
                "created_at": row.get("created_at"),
                "is_author_account": login in AUTHOR_LOGINS,
                "body_preview": (row.get("body") or "").strip().replace("\r\n", "\n")[:160],
            }
        )
    return rows


def main() -> int:
    comments = _fetch_discussion_comments()
    external = [c for c in comments if not c["is_author_account"]]
    external_repro_like = [
        c
        for c in external
        if any(k in (c.get("body_preview") or "").lower() for k in ("python", "ok", "exit", "linux", "macos", "windows"))
    ]

    poll = {
        "schema": "universal_root_community_poll_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "discussion": {
            "repo": REPO,
            "number": DISCUSSION,
            "url": f"https://github.com/{REPO}/discussions/{DISCUSSION}",
            "comment_count": len(comments),
            "author_comment_count": len(comments) - len(external),
            "external_comment_count": len(external),
            "external_repro_like_count": len(external_repro_like),
            "comments": comments,
        },
        "reproduce": "py scripts/poll_universal_root_community_gtm_v1.py",
    }

    if GTM.is_file():
        doc = json.loads(GTM.read_text(encoding="utf-8-sig"))
        doc["updated_at_utc"] = _utc()
        gh = doc.setdefault("channels", {}).setdefault("github_discussions", {})
        gh["external_repro_reports"] = len(external_repro_like) or len(external)
        gh["last_poll_utc"] = poll["generated_at_utc"]
        gh["comment_count"] = len(comments)
        gh["status"] = (
            "external_repro_received" if external_repro_like else "awaiting_external_repro"
        )
        if external_repro_like:
            milestones = doc.setdefault("milestones", {})
            milestones["UR-W1"] = {
                "status": "complete",
                "note": f"external repro reports={len(external_repro_like)} on Discussions #{DISCUSSION}",
            }
            doc["next_actions"] = [
                a
                for a in (doc.get("next_actions") or [])
                if "external repro" not in a.lower()
            ]
        GTM.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(poll, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "external_repro_like": len(external_repro_like),
                "out": str(OUT),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        raise SystemExit(1) from exc
