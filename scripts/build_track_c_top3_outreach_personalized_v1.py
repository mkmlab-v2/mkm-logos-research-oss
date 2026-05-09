#!/usr/bin/env python3
"""Build personalized-ready outreach messages from Top3 outreach pack."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _replace_tokens(text: str, *, company: str, contact: str, option1: str, option2: str, sender: str) -> str:
    rendered = (
        text.replace("[회사명]", company)
        .replace("[담당자명]", contact)
        .replace("[옵션1]", option1)
        .replace("[옵션2]", option2)
        .replace("[보내는이]", sender)
    )
    return rendered.replace("님님", "님")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate personalized Top3 outreach messages.")
    parser.add_argument("--contact-default", default="담당자님", help="Default contact placeholder replacement.")
    parser.add_argument("--option1", default="이번 주 수요일 14:00", help="Meeting option 1.")
    parser.add_argument("--option2", default="이번 주 목요일 10:30", help="Meeting option 2.")
    parser.add_argument("--sender", default="MKM Track C 팀", help="Sender signature.")
    args = parser.parse_args()

    root = _root()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    src = root / "docs/final/artifacts/track_c_b2b_outreach_top3_pack_latest.json"
    pack = _load_json(src)
    targets = pack.get("targets", [])

    rendered = []
    for item in targets:
        company = item["name"]
        contact = args.contact_default
        subject = _replace_tokens(
            item["subject"],
            company=company,
            contact=contact,
            option1=args.option1,
            option2=args.option2,
            sender=args.sender,
        )
        body = _replace_tokens(
            item["body"],
            company=company,
            contact=contact,
            option1=args.option1,
            option2=args.option2,
            sender=args.sender,
        )
        rendered.append(
            {
                "rank": item["rank"],
                "company": company,
                "segment": item["segment"],
                "score": item["score"],
                "subject": subject,
                "body": body,
            }
        )

    out_json = root / "docs/final/artifacts/track_c_b2b_outreach_top3_personalized_latest.json"
    out_md = root / "docs/final/artifacts/track_c_b2b_outreach_top3_personalized_latest.md"
    payload = {
        "schema": "track_c_b2b_outreach_top3_personalized_v1",
        "generated_at_utc": now,
        "source_pack": str(src.relative_to(root)).replace("\\", "/"),
        "meeting_options": {"option1": args.option1, "option2": args.option2},
        "sender": args.sender,
        "messages": rendered,
    }
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Track C Top3 Outreach Personalized (Latest)",
        "",
        f"- generated_at_utc: `{now}`",
        "- schema: `track_c_b2b_outreach_top3_personalized_v1`",
        f"- option1: `{args.option1}`",
        f"- option2: `{args.option2}`",
        f"- sender: `{args.sender}`",
        "",
    ]
    for m in rendered:
        lines.extend(
            [
                f"## {m['rank']}) {m['company']} ({m['segment']})",
                "",
                f"### 제목",
                "",
                m["subject"],
                "",
                "### 본문",
                "",
                m["body"],
                "",
                "---",
                "",
            ]
        )
    out_md.write_text("\n".join(lines), encoding="utf-8")

    print(f"Wrote {out_json}")
    print(f"Wrote {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

