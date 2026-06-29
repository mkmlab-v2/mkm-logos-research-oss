#!/usr/bin/env python3
"""Create mkm-bible-topology-crosswalk GitHub Discussion via gh GraphQL."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BODY = ROOT / "reports/_bible_topology_discussion_body.md"
OUT = ROOT / "reports/bible_topology_github_discussion_v1_latest.json"

QUERY = """
mutation($input: CreateDiscussionInput!) {
  createDiscussion(input: $input) {
    discussion {
      url
      title
      number
    }
  }
}
""".strip()


def main() -> int:
    body_text = BODY.read_text(encoding="utf-8")
    payload = {
        "query": QUERY,
        "variables": {
            "input": {
                "repositoryId": "R_kgDOTBASVw",
                "categoryId": "DIC_kwDOTBASV84C_moc",
                "title": "Reproduce Tier A passion-week topology lint on your machine?",
                "body": body_text,
            }
        },
    }
    proc = subprocess.run(
        ["gh", "api", "graphql", "--input", "-"],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        cwd=str(ROOT),
        check=False,
    )
    doc: dict = {
        "ok": proc.returncode == 0,
        "exit_code": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }
    if proc.returncode == 0 and proc.stdout.strip():
        try:
            parsed = json.loads(proc.stdout)
            discussion = parsed.get("data", {}).get("createDiscussion", {}).get("discussion", {})
            doc["discussion_url"] = discussion.get("url")
            doc["discussion_number"] = discussion.get("number")
        except json.JSONDecodeError:
            pass
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["ok"], "discussion_url": doc.get("discussion_url")}, ensure_ascii=False))
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
