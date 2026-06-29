#!/usr/bin/env python3
"""Record Show HN post URL into GTM JSON after commander manual submit."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GTM = ROOT / "reports/universal_root_community_gtm_v1_latest.json"
OUT = ROOT / "reports/universal_root_show_hn_post_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _valid_hn_url(url: str) -> bool:
    return bool(re.match(r"^https?://news\.ycombinator\.com/item\?id=\d+", url.strip()))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--url", required=True, help="https://news.ycombinator.com/item?id=...")
    args = ap.parse_args()
    url = args.url.strip()
    if not _valid_hn_url(url):
        raise SystemExit("url must be news.ycombinator.com/item?id=NNN")

    gtm: dict[str, Any] = {}
    if GTM.is_file():
        gtm = json.loads(GTM.read_text(encoding="utf-8-sig"))

    hn = gtm.setdefault("channels", {}).setdefault("show_hn", {})
    hn.update(
        {
            "status": "posted",
            "posted_at_utc": _utc(),
            "posted_by": "commander",
            "post_url": url,
            "handle": "moksorinw",
            "paste_ssot": "reports/human_paste/universal_root_show_hn_title.txt · universal_root_show_hn_body.md · universal_root_show_hn_first_comment.md",
        }
    )
    GTM.write_text(json.dumps(gtm, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    doc = {
        "schema": "universal_root_show_hn_post_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "ok": True,
        "post_url": url,
        "gtm": str(GTM.relative_to(ROOT)).replace("\\", "/"),
        "reproduce": "py scripts/record_universal_root_show_hn_post_v1.py --url <item_url>",
    }
    OUT.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "post_url": url, "out": str(OUT).replace("\\", "/")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
