#!/usr/bin/env python3
"""Post maintainer repro note on mkm-bible-topology-crosswalk Discussion #1."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/bible_topology_discussion_author_note_v1_latest.json"
DISCUSSION_ID = "D_kwDOTBASV84AnRgl"

BODY = """Maintainer note — quick repro path on this repo:

```bash
git clone https://github.com/mkmlab-v2/mkm-bible-topology-crosswalk.git
cd mkm-bible-topology-crosswalk && pip install -r requirements.txt
python3 scripts/run_bible_topology_oss_smoke_v1.py
```

Parent engine (run first if new): https://github.com/mkmlab-v2/mkm-universal-root

Sibling link-back posted on Universal Root Discussion #2. Tier A seed only — not full 63k / not Harrison graphics.
"""

QUERY = """
mutation($input: AddDiscussionCommentInput!) {
  addDiscussionComment(input: $input) {
    comment { url }
  }
}
""".strip()


def main() -> int:
    payload = {
        "query": QUERY,
        "variables": {"input": {"discussionId": DISCUSSION_ID, "body": BODY}},
    }
    proc = subprocess.run(
        ["gh", "api", "graphql", "--input", "-"],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        cwd=str(ROOT),
        check=False,
    )
    doc = {"ok": proc.returncode == 0, "stdout": proc.stdout.strip(), "stderr": proc.stderr.strip()}
    if proc.returncode == 0 and proc.stdout.strip():
        try:
            url = (
                json.loads(proc.stdout)
                .get("data", {})
                .get("addDiscussionComment", {})
                .get("comment", {})
                .get("url")
            )
            doc["comment_url"] = url
        except json.JSONDecodeError:
            pass
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["ok"], "comment_url": doc.get("comment_url")}, ensure_ascii=False))
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
