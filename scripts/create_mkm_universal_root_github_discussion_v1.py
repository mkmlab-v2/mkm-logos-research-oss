#!/usr/bin/env python3
"""Create mkm-universal-root GitHub Discussion via gh GraphQL."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BODY = ROOT / "reports/_community_launch_discussion_body.md"
OUT = ROOT / "reports/community_launch_github_discussion_v1_latest.json"

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

PAYLOAD = {
    "query": QUERY,
    "variables": {
        "input": {
            "repositoryId": "R_kgDOTA0_2w",
            "categoryId": "DIC_kwDOTA0_284C_mCl",
            "title": "Reproduce the 20s smoke on your machine? (OS / Python version report)",
            "body": BODY.read_text(encoding="utf-8"),
        }
    },
}


def main() -> int:
    proc = subprocess.run(
        ["gh", "api", "graphql", "--input", "-"],
        input=json.dumps(PAYLOAD),
        text=True,
        capture_output=True,
        cwd=str(ROOT),
        check=False,
    )
    doc = {
        "ok": proc.returncode == 0,
        "exit_code": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }
    if proc.returncode == 0 and proc.stdout.strip():
        try:
            parsed = json.loads(proc.stdout)
            url = parsed.get("data", {}).get("createDiscussion", {}).get("discussion", {}).get("url")
            doc["discussion_url"] = url
        except json.JSONDecodeError:
            pass
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["ok"], "discussion_url": doc.get("discussion_url"), "out": str(OUT)}, ensure_ascii=False))
    if proc.stderr:
        print(proc.stderr, file=sys.stderr)
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
