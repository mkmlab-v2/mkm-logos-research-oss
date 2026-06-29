#!/usr/bin/env python3
"""Post link-back comment on mkm-universal-root Discussion #2 for sibling bible topology repo."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/bible_topology_universal_root_linkback_v1_latest.json"

DISCUSSION_ID = "D_kwDOTA0_284AnRYe"
BODY = """Sibling extension (topology contributor shards): https://github.com/mkmlab-v2/mkm-bible-topology-crosswalk

Parent smoke still: `run_universal_root_oss_cursor_smoke_v1.py` — this repo adds Tier A Bible edge lint only.

- Live CI: `topology-contrib-lint` on main
- Repro thread: https://github.com/mkmlab-v2/mkm-bible-topology-crosswalk/discussions/1
- `research_only` · `send_gate: HOLD` — not a full 63k corpus or Harrison graphics bundle
"""

QUERY = """
mutation($input: AddDiscussionCommentInput!) {
  addDiscussionComment(input: $input) {
    comment {
      url
      bodyText
    }
  }
}
""".strip()


def main() -> int:
    payload = {
        "query": QUERY,
        "variables": {
            "input": {
                "discussionId": DISCUSSION_ID,
                "body": BODY,
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
            comment = parsed.get("data", {}).get("addDiscussionComment", {}).get("comment", {})
            doc["comment_url"] = comment.get("url")
        except json.JSONDecodeError:
            pass
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["ok"], "comment_url": doc.get("comment_url")}, ensure_ascii=False))
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
