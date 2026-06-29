#!/usr/bin/env python3
"""Post Thread A bump to GitHub Discussions #2 (author follow-up · not X/Reddit auto-post)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.universal_root_gtm_freeze_lib_v1 import evaluate_gtm_freeze  # noqa: E402

DEFAULT_BODY = ROOT / "reports/human_paste/universal_root_discussions_thread_a_bump.md"
OUT = ROOT / "reports/universal_root_discussions_bump_post_v1_latest.json"
REPO = "mkmlab-v2/mkm-universal-root"
DISCUSSION = 2


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--body-file",
        type=Path,
        default=DEFAULT_BODY,
        help="Markdown/text body (default: thread_a_bump.md; repro: universal_root_discussions_thread_a_repro_reply.md)",
    )
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--commander-override-freeze",
        action="store_true",
        help="Bypass GTM FREEZE for live post (commander only)",
    )
    args = ap.parse_args()

    body_path = args.body_file if args.body_file.is_absolute() else ROOT / args.body_file
    if not body_path.is_file():
        print(json.dumps({"ok": False, "error": "body_file_missing", "path": str(body_path)}))
        return 1

    text = body_path.read_text(encoding="utf-8-sig").strip()
    doc = {
        "schema": "universal_root_discussions_bump_post_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "discussion_url": f"https://github.com/{REPO}/discussions/{DISCUSSION}",
        "body_file": str(body_path.relative_to(ROOT)).replace("\\", "/"),
        "body_chars": len(text),
        "dry_run": args.dry_run,
    }

    if args.dry_run:
        doc["ok"] = True
        doc["body_preview"] = text[:240]
        OUT.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps({"ok": True, "dry_run": True, "out": str(OUT)}, ensure_ascii=False))
        return 0

    freeze_ev = evaluate_gtm_freeze(
        action="discussions_live_post",
        commander_override=args.commander_override_freeze,
    )
    doc["gtm_freeze_eval"] = freeze_ev
    if not freeze_ev.get("ok"):
        doc["ok"] = False
        doc["error"] = "gtm_freeze_blocked"
        OUT.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps({"ok": False, "error": "gtm_freeze_blocked", "violations": freeze_ev.get("violations")}))
        return 3

    id_proc = subprocess.run(
        [
            "gh",
            "api",
            "graphql",
            "-f",
            "query=query{repository(owner:\"mkmlab-v2\",name:\"mkm-universal-root\"){discussion(number:2){id}}}",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if id_proc.returncode != 0:
        doc["ok"] = False
        doc["stderr"] = (id_proc.stderr or id_proc.stdout or "discussion id lookup failed")[:500]
        OUT.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps({"ok": False, "out": str(OUT)}, ensure_ascii=False))
        return 1

    discussion_id = (
        json.loads(id_proc.stdout or "{}")
        .get("data", {})
        .get("repository", {})
        .get("discussion", {})
        .get("id")
    )
    if not discussion_id:
        doc["ok"] = False
        doc["stderr"] = "discussion_id_missing"
        OUT.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps({"ok": False, "out": str(OUT)}, ensure_ascii=False))
        return 1

    mutation = (
        "mutation($id:ID!,$body:String!){addDiscussionComment(input:{discussionId:$id,body:$body})"
        "{comment{url id}}}"
    )
    proc = subprocess.run(
        [
            "gh",
            "api",
            "graphql",
            "-f",
            f"query={mutation}",
            "-f",
            f"id={discussion_id}",
            "-f",
            f"body={text}",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    doc["gh_exit_code"] = proc.returncode
    if proc.returncode != 0:
        doc["ok"] = False
        doc["stderr"] = (proc.stderr or proc.stdout or "").strip()[:500]
        OUT.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps({"ok": False, "out": str(OUT)}, ensure_ascii=False))
        return 1

    try:
        resp = json.loads(proc.stdout or "{}")
        if resp.get("errors"):
            doc["ok"] = False
            doc["stderr"] = json.dumps(resp["errors"])[:500]
            OUT.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            print(json.dumps({"ok": False, "out": str(OUT)}, ensure_ascii=False))
            return 1
        comment = (resp.get("data") or {}).get("addDiscussionComment", {}).get("comment") or {}
        doc["ok"] = True
        doc["comment_id"] = comment.get("id")
        doc["html_url"] = comment.get("url")
    except json.JSONDecodeError:
        doc["ok"] = True
        doc["raw_stdout"] = (proc.stdout or "")[:500]

    OUT.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(OUT)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
