#!/usr/bin/env python3
"""Create Universal Root GitHub Discussions Thread B (music P1 research · after Thread A traction)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PASTE = ROOT / "reports/human_paste"
DEFAULT_TITLE = PASTE / "universal_root_discussions_thread_b_title.txt"
DEFAULT_BODY = PASTE / "universal_root_discussions_thread_b_body.md"
OUT = ROOT / "reports/universal_root_discussions_thread_b_post_v1_latest.json"
GTM = ROOT / "reports/universal_root_community_gtm_v1_latest.json"
REPO = "mkmlab-v2/mkm-universal-root"
POLL = ROOT / "reports/universal_root_community_poll_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_gtm_external_repro() -> int:
    if GTM.is_file():
        doc = json.loads(GTM.read_text(encoding="utf-8-sig"))
        return int(
            (doc.get("channels") or {})
            .get("github_discussions", {})
            .get("external_repro_reports", 0)
            or 0
        )
    if POLL.is_file():
        poll = json.loads(POLL.read_text(encoding="utf-8-sig"))
        disc = poll.get("discussion") or {}
        return int(disc.get("external_repro_like_count") or disc.get("external_comment_count") or 0)
    return 0


def _repo_and_category_ids() -> tuple[str, str]:
    query = (
        "query{repository(owner:\"mkmlab-v2\",name:\"mkm-universal-root\")"
        "{id discussionCategories(first:10){nodes{id name}}}}"
    )
    proc = subprocess.run(
        ["gh", "api", "graphql", "-f", f"query={query}"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or "graphql repo lookup failed").strip())
    data = json.loads(proc.stdout or "{}")
    if data.get("errors"):
        raise RuntimeError(json.dumps(data["errors"])[:500])
    repo = (data.get("data") or {}).get("repository") or {}
    repo_id = repo.get("id")
    nodes = ((repo.get("discussionCategories") or {}).get("nodes")) or []
    category_id = None
    for node in nodes:
        name = str(node.get("name") or "").lower()
        if name in {"general", "q&a", "ideas"}:
            category_id = node.get("id")
            if name == "general":
                break
    if not category_id and nodes:
        category_id = nodes[0].get("id")
    if not repo_id or not category_id:
        raise RuntimeError("repository_or_category_id_missing")
    return str(repo_id), str(category_id)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--title-file", type=Path, default=DEFAULT_TITLE)
    ap.add_argument("--body-file", type=Path, default=DEFAULT_BODY)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--acknowledge-send",
        action="store_true",
        help="R4 ack for live Discussions create (send_gate HOLD)",
    )
    ap.add_argument(
        "--min-external-repro",
        type=int,
        default=1,
        help="Block live post until Thread A external repro count >= N (default 1)",
    )
    ap.add_argument("--force", action="store_true", help="Skip external repro gate (commander override)")
    args = ap.parse_args()

    title_path = args.title_file if args.title_file.is_absolute() else ROOT / args.title_file
    body_path = args.body_file if args.body_file.is_absolute() else ROOT / args.body_file
    if not title_path.is_file() or not body_path.is_file():
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "paste_missing",
                    "title": str(title_path),
                    "body": str(body_path),
                },
                ensure_ascii=False,
            )
        )
        return 1

    title = title_path.read_text(encoding="utf-8-sig").strip()
    body = body_path.read_text(encoding="utf-8-sig").strip()
    external_repro = _load_gtm_external_repro()

    doc: dict = {
        "schema": "universal_root_discussions_thread_b_post_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "repo": REPO,
        "title_file": str(title_path.relative_to(ROOT)).replace("\\", "/"),
        "body_file": str(body_path.relative_to(ROOT)).replace("\\", "/"),
        "title_chars": len(title),
        "body_chars": len(body),
        "external_repro_reports": external_repro,
        "min_external_repro": args.min_external_repro,
        "dry_run": args.dry_run,
    }

    if args.dry_run:
        try:
            repo_id, category_id = _repo_and_category_ids()
            doc["ok"] = True
            doc["repository_id"] = repo_id
            doc["category_id"] = category_id
            doc["title_preview"] = title[:120]
            doc["body_preview"] = body[:240]
            doc["gate"] = (
                "ready_for_live"
                if args.force or external_repro >= args.min_external_repro
                else "blocked_await_external_repro"
            )
        except RuntimeError as exc:
            doc["ok"] = False
            doc["error"] = str(exc)
        OUT.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps({"ok": doc.get("ok"), "dry_run": True, "gate": doc.get("gate"), "out": str(OUT)}))
        return 0 if doc.get("ok") else 1

    if not args.acknowledge_send:
        doc["ok"] = False
        doc["error"] = "acknowledge_send_required"
        OUT.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps({"ok": False, "error": "acknowledge_send_required"}, ensure_ascii=False))
        return 2

    if not args.force and external_repro < args.min_external_repro:
        doc["ok"] = False
        doc["error"] = f"external_repro_gate:{external_repro}<{args.min_external_repro}"
        OUT.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps({"ok": False, "error": doc["error"]}, ensure_ascii=False))
        return 3

    try:
        repo_id, category_id = _repo_and_category_ids()
    except RuntimeError as exc:
        doc["ok"] = False
        doc["error"] = str(exc)
        OUT.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1

    mutation = (
        "mutation($repo:ID!,$cat:ID!,$title:String!,$body:String!)"
        "{createDiscussion(input:{repositoryId:$repo,categoryId:$cat,title:$title,body:$body})"
        "{discussion{url number id}}}"
    )
    proc = subprocess.run(
        [
            "gh",
            "api",
            "graphql",
            "-f",
            f"query={mutation}",
            "-f",
            f"repo={repo_id}",
            "-f",
            f"cat={category_id}",
            "-f",
            f"title={title}",
            "-f",
            f"body={body}",
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

    resp = json.loads(proc.stdout or "{}")
    if resp.get("errors"):
        doc["ok"] = False
        doc["stderr"] = json.dumps(resp["errors"])[:500]
        OUT.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps({"ok": False, "out": str(OUT)}, ensure_ascii=False))
        return 1

    discussion = (resp.get("data") or {}).get("createDiscussion", {}).get("discussion") or {}
    doc["ok"] = True
    doc["discussion_url"] = discussion.get("url")
    doc["discussion_number"] = discussion.get("number")
    doc["discussion_id"] = discussion.get("id")

    if GTM.is_file():
        gtm_doc = json.loads(GTM.read_text(encoding="utf-8-sig"))
        gh = gtm_doc.setdefault("channels", {}).setdefault("github_discussions", {})
        gh["thread_b_status"] = "posted"
        gh["thread_b_url"] = discussion.get("url")
        gh["thread_b_number"] = discussion.get("number")
        gtm_doc["updated_at_utc"] = _utc()
        GTM.write_text(json.dumps(gtm_doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    OUT.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "url": discussion.get("url"), "out": str(OUT)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
