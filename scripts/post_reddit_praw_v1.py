#!/usr/bin/env python3
"""Post to Reddit via official API (PRAW) — preferred path for r/LocalLLM GTM.

Playwright openchrome (`post_bible_topology_community_openchrome_v1.py`) = prefill/smoke only.

Secrets (DPAPI via security_agent_manager or env):
  MKM_REDDIT_CLIENT_ID / MKM_REDDIT_CLIENT_SECRET
  MKM_COMMUNITY_REDDIT_USERNAME / MKM_COMMUNITY_REDDIT_PASSWORD
  MKM_REDDIT_USER_AGENT (optional; default includes username)

Register app: https://www.reddit.com/prefs/apps → script app → copy client id + secret.
Store:
  powershell -File scripts\\Invoke-EncryptedSecretStore.ps1 -Action set -Key MKM_REDDIT_CLIENT_ID
  powershell -File scripts\\Invoke-EncryptedSecretStore.ps1 -Action set -Key MKM_REDDIT_CLIENT_SECRET

Paste SSOT packs under reports/human_paste/ (see --pack).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/reddit_praw_post_v1_latest.json"
PASTE = ROOT / "reports/human_paste"

PACKS: dict[str, dict[str, Path]] = {
    "bible_topology": {
        "title": PASTE / "bible_topology_reddit_title.txt",
        "body": PASTE / "bible_topology_reddit_body.md",
    },
    "universal_root": {
        "title": PASTE / "universal_root_reddit_title.txt",
        "body": PASTE / "universal_root_reddit_body.md",
    },
}


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _resolve_secret(name: str) -> str | None:
    val = (os.environ.get(name) or "").strip()
    if val:
        return val
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT / "scripts"))
    try:
        from security_agent_manager import get_security_agent  # type: ignore

        got = get_security_agent().get_env_var(name)
        if got and got.strip():
            return got.strip()
    except Exception:
        pass
    return None


def _reddit_creds() -> dict[str, str]:
    client_id = _resolve_secret("MKM_REDDIT_CLIENT_ID")
    client_secret = _resolve_secret("MKM_REDDIT_CLIENT_SECRET")
    username = _resolve_secret("MKM_COMMUNITY_REDDIT_USERNAME") or _resolve_secret("MKM_REDDIT_USERNAME")
    password = _resolve_secret("MKM_COMMUNITY_REDDIT_PASSWORD") or _resolve_secret("MKM_REDDIT_PASSWORD")
    missing = [k for k, v in {
        "MKM_REDDIT_CLIENT_ID": client_id,
        "MKM_REDDIT_CLIENT_SECRET": client_secret,
        "MKM_COMMUNITY_REDDIT_USERNAME": username,
        "MKM_COMMUNITY_REDDIT_PASSWORD": password,
    }.items() if not v]
    if missing:
        raise RuntimeError(f"missing_reddit_credentials:{','.join(missing)}")
    user_agent = (
        _resolve_secret("MKM_REDDIT_USER_AGENT")
        or f"mkm-gtm-praw/1.0 (by u/{username})"
    )
    return {
        "client_id": client_id or "",
        "client_secret": client_secret or "",
        "username": username or "",
        "password": password or "",
        "user_agent": user_agent,
    }


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig").strip()


def resolve_flair_id(subreddit: Any, flair_label: str) -> str | None:
    want = flair_label.strip().lower()
    for choice in subreddit.flair.link_templates.user_selectable():
        text = (choice.get("text") or "").strip()
        if text.lower() == want:
            return choice.get("id") or choice.get("flair_template_id")
    return None


def list_flair_labels(subreddit: Any) -> list[str]:
    return [
        (c.get("text") or "").strip()
        for c in subreddit.flair.link_templates.user_selectable()
        if (c.get("text") or "").strip()
    ]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pack", choices=sorted(PACKS), help="Paste bundle under reports/human_paste/")
    ap.add_argument("--subreddit", default="LocalLLM")
    ap.add_argument("--title-file", type=Path)
    ap.add_argument("--body-file", type=Path)
    ap.add_argument("--flair", default="Discussion", help="Link flair text (default Discussion)")
    ap.add_argument("--dry-run", action="store_true", help="Auth + list flairs; do not submit")
    ap.add_argument("--list-flairs", action="store_true", help="Print selectable flairs and exit")
    ap.add_argument(
        "--acknowledge-send",
        action="store_true",
        help="R4: commander ack required for live submit (send_gate default HOLD)",
    )
    args = ap.parse_args()

    if args.pack:
        title_path = PACKS[args.pack]["title"]
        body_path = PACKS[args.pack]["body"]
    else:
        title_path = args.title_file
        body_path = args.body_file
    if not title_path or not body_path:
        ap.error("Provide --pack or both --title-file and --body-file")
    if not title_path.is_file() or not body_path.is_file():
        raise SystemExit(f"paste_missing:{title_path} or {body_path}")

    title = _read(title_path)
    body = _read(body_path)

    report: dict[str, Any] = {
        "schema": "reddit_praw_post_v1",
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "track": "B-track",
        "generated_at_utc": _utc(),
        "subreddit": args.subreddit,
        "pack": args.pack,
        "title_file": str(title_path.relative_to(ROOT)).replace("\\", "/"),
        "body_file": str(body_path.relative_to(ROOT)).replace("\\", "/"),
        "title_len": len(title),
        "body_len": len(body),
        "flair_requested": args.flair,
        "dry_run": args.dry_run,
        "acknowledge_send": args.acknowledge_send,
        "ok": False,
    }

    if not args.dry_run and not args.list_flairs and not args.acknowledge_send:
        report["error"] = "send_gate_hold"
        report["status"] = "blocked_governance"
        OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"ok": False, "error": report["error"]}, ensure_ascii=False))
        return 5

    try:
        import praw  # type: ignore
    except ImportError:
        report["error"] = "praw_not_installed: pip install -r scripts/requirements-mkm-reddit-praw.txt"
        OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"ok": False, "error": report["error"]}, ensure_ascii=False))
        return 2

    try:
        creds = _reddit_creds()
    except RuntimeError as exc:
        report["error"] = str(exc)
        OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"ok": False, "error": report["error"]}, ensure_ascii=False))
        return 3

    reddit = praw.Reddit(**creds)
    me = reddit.user.me()
    report["authenticated_as"] = str(me) if me else None
    sub = reddit.subreddit(args.subreddit)
    flairs = list_flair_labels(sub)
    report["flairs_available"] = flairs
    flair_id = resolve_flair_id(sub, args.flair) if args.flair else None
    report["flair_id"] = flair_id

    if args.list_flairs or args.dry_run:
        report["ok"] = True
        report["status"] = "dry_run" if args.dry_run else "list_flairs"
        OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"ok": True, "status": report["status"], "flairs": flairs, "flair_id": flair_id}, ensure_ascii=False))
        return 0

    if args.flair and not flair_id:
        report["error"] = f"flair_not_found:{args.flair}"
        report["flairs_available"] = flairs
        OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"ok": False, "error": report["error"], "flairs": flairs}, ensure_ascii=False))
        return 4

    submit_kwargs: dict[str, Any] = {"title": title, "selftext": body}
    if flair_id:
        submit_kwargs["flair_id"] = flair_id

    submission = sub.submit(**submit_kwargs)
    report["ok"] = True
    report["status"] = "posted"
    report["permalink"] = f"https://www.reddit.com{submission.permalink}"
    report["submission_id"] = submission.id
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "permalink": report["permalink"], "id": submission.id}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
