#!/usr/bin/env python3
"""Export LinkedIn paste files: full checklist body + public composer body (no internal gates)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PASTE_DIR = ROOT / "reports/marketing/linkedin_paste_ready"
PRIMARY_TXT = ROOT / "reports/marketing/linkedin_paste_primary_latest.txt"
DEFAULT_PRIMARY_ID = "showroom_topology_observability_ko"
def _public_body(body: str) -> str:
    from scripts.push_marketing_draft_to_buffer_v1 import _strip_leading_draft_marker

    body = _strip_leading_draft_marker(body)
    lines = body.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        s = line.strip()
        if s.startswith("## Human gate") or s.startswith("## B-roll"):
            break
        if s.startswith("## Source artifacts"):
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("## "):
                i += 1
            continue
        out.append(line)
        i += 1
    return "\n".join(out).strip()


def export_from_ready(doc: dict[str, Any], *, primary_id: str) -> dict[str, Any]:
    PASTE_DIR.mkdir(parents=True, exist_ok=True)
    exports: list[dict[str, Any]] = []
    primary_public: str | None = None

    for post in doc.get("posts") or []:
        if not isinstance(post, dict) or not post.get("ok"):
            continue
        iid = str(post.get("id") or "")
        body = str(post.get("post_body") or "")
        if not iid or not body:
            continue
        full_path = PASTE_DIR / f"{iid}_paste.txt"
        public_path = PASTE_DIR / f"{iid}_public.txt"
        full_path.write_text(body + "\n", encoding="utf-8")
        pub = _public_body(body)
        public_path.write_text(pub + "\n", encoding="utf-8")
        if iid == primary_id:
            primary_public = pub
        exports.append(
            {
                "id": iid,
                "full_paste": full_path.relative_to(ROOT).as_posix(),
                "public_paste": public_path.relative_to(ROOT).as_posix(),
                "public_char_count": len(pub),
            }
        )

    if primary_public is None and exports:
        first = next(p for p in doc.get("posts") or [] if isinstance(p, dict) and p.get("ok"))
        primary_public = _public_body(str(first.get("post_body") or ""))

    if primary_public:
        PRIMARY_TXT.write_text(primary_public + "\n", encoding="utf-8")

    return {
        "ok": bool(exports),
        "schema": "marketing_linkedin_paste_exports_v1",
        "primary_id": primary_id,
        "primary_txt": PRIMARY_TXT.relative_to(ROOT).as_posix() if primary_public else None,
        "exports": exports,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--queue", type=Path, default=ROOT / "data/marketing/marketing_content_queue.json")
    ap.add_argument(
        "--primary-id",
        default=os.environ.get("MKM_LINKEDIN_PASTE_PRIMARY_ID", DEFAULT_PRIMARY_ID),
        help="Queue item id for linkedin_paste_primary_latest.txt",
    )
    ap.add_argument("--out-json", type=Path, default=ROOT / "reports/marketing/marketing_linkedin_paste_exports_latest.json")
    args = ap.parse_args()

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts.build_marketing_linkedin_post_ready_v1 import build

    ready = build(queue_path=args.queue)
    if not ready.get("ok"):
        print(json.dumps({"ok": False, "error": "post_ready_build_failed"}, ensure_ascii=False))
        return 2

    pack = export_from_ready(ready, primary_id=str(args.primary_id))
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": pack.get("ok"), "output": str(args.out_json), "primary": pack.get("primary_txt")}, ensure_ascii=False))
    return 0 if pack.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
