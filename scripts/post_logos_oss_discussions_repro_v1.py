#!/usr/bin/env python3
"""Post Logos OSS Y1c GitHub Discussions repro thread (General)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PASTE = ROOT / "reports/human_paste"
DEFAULT_TITLE = PASTE / "logos_oss_discussions_repro_title.txt"
DEFAULT_BODY = PASTE / "logos_oss_discussions_repro_body.md"
OUT = ROOT / "reports/logos_oss_discussions_repro_post_v1_latest.json"
REPO = "mkmlab-v2/mkm-logos-research-oss"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _repo_and_category_ids() -> tuple[str, str]:
    query = (
        f'query{{repository(owner:"mkmlab-v2",name:"mkm-logos-research-oss")'
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
    args = ap.parse_args()

    title = args.title_file.read_text(encoding="utf-8").strip()
    body = args.body_file.read_text(encoding="utf-8").strip()
    if not title or not body:
        raise SystemExit("title/body paste files missing or empty")

    doc: dict = {
        "schema": "logos_oss_discussions_repro_post_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "repo": REPO,
        "title": title,
        "body_chars": len(body),
        "dry_run": args.dry_run,
    }

    if args.dry_run:
        doc["ok"] = True
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"ok": True, "dry_run": True, "out": str(OUT)}, ensure_ascii=False))
        return 0

    repo_id, category_id = _repo_and_category_ids()
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
    if proc.returncode != 0:
        doc["ok"] = False
        doc["error"] = (proc.stderr or proc.stdout or "")[:1000]
        OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"ok": False, "error": doc["error"]}, ensure_ascii=False))
        return 1

    data = json.loads(proc.stdout or "{}")
    if data.get("errors"):
        doc["ok"] = False
        doc["error"] = json.dumps(data["errors"])[:1000]
        OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return 1

    discussion = ((data.get("data") or {}).get("createDiscussion") or {}).get("discussion") or {}
    doc.update(
        {
            "ok": True,
            "discussion_url": discussion.get("url"),
            "discussion_number": discussion.get("number"),
        }
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "discussion_url": doc.get("discussion_url"), "out": str(OUT)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
