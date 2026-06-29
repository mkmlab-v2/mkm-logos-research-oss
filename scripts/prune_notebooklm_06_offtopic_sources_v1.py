#!/usr/bin/env python3
"""Delete NL 06 sources classified as off-topic (delete bucket only).

Respects commander policy: does NOT delete 'review' bucket (aggressive prune paused).
Uses same rules as build_notebooklm_06_prune_candidates_v1.py.

SSOT: reports/notebooklm_06_source_cleanup_guide_v1.md
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NB_DEFAULT = "96865180-769e-4a77-89bb-5f03a8083ac3"
OUT_DEFAULT = ROOT / "reports" / "notebooklm_06_offtopic_prune_result_v1_latest.json"

KEEP_SUBSTRINGS = [
    "smartfarm_geumsan",
    "golden40",
    "compression_track_a",
    "GEUMSAN_IOT",
    "00_ops_handoff",
    "farm.jema-ai.com/smartfarm",
    "revision_email",
    "gonogo",
    "vendor_rfq",
    "vendor_outreach",
    "autopilot_brief",
    "QuBics",
    "견적",
    "목소리",
    "큐빅",
    "qubics",
    # Regional project clips (NL 06 review → keep, not orphan)
    "금산",
    "진도군",
    "금산인삼",
    "GAP인증",
]

# Aggressive review prune: goldsan/IoT/project hints stay; generic web clips go.
AGGRESSIVE_KEEP_HINTS = (
    "금산",
    "진도",
    "목소리",
    "큐빅",
    "QuBIC",
    "견적",
    "260520",
    "260522",
    "smartfarm",
    "golden40",
    "compression_track",
    "ops_handoff",
    "GEUMSAN",
    "farm.jema",
    "[KEEP]",
    "[이관]",
)

DELETE_KEYWORDS = [
    "LG",
    "압축",
    "compression",
    "Golden 40",
    "예언",
    "prophecy",
    "LOGOS",
    "Track C",
    "MASTER",
    "OPS_COMMAND",
    "명리",
    "만세력",
    "SBA",
    "붙여넣은 텍스트",
    "MS RQ",
    "defense",
    "oracle_v",
    "inter-agent",
]


def base_title(raw: str) -> str:
    t = (raw or "").strip()
    if "__p" in t:
        t = t.split("__p", 1)[0]
    t = re.sub(r"\s*\(sync\s+[^)]+\)\s*$", "", t, flags=re.I)
    return t.strip()


def aggressive_review_is_delete(title: str) -> bool:
    return not any(h.lower() in title.lower() or h in title for h in AGGRESSIVE_KEEP_HINTS)


def classify(title: str, *, aggressive_review: bool = False) -> str:
    low = title.lower()
    for k in KEEP_SUBSTRINGS:
        if k.lower() in low or k in title:
            return "keep"
    for k in DELETE_KEYWORDS:
        if k.lower() in low or k in title:
            return "delete"
    if title.startswith("[KEEP]") or "[KEEP]" in title:
        return "keep"
    if title.startswith("[HOLD]") or title.startswith("[이관]"):
        if aggressive_review and aggressive_review_is_delete(title):
            return "delete"
        return "review"
    if aggressive_review and aggressive_review_is_delete(title):
        return "delete"
    return "review"


def fetch_sources(notebook_id: str) -> list[dict]:
    raw = subprocess.check_output(
        ["nlm", "notebook", "get", notebook_id, "--json"],
        text=True,
        encoding="utf-8-sig",
    )
    data = json.loads(raw)
    val = data.get("value", data)
    return list(val.get("sources") or [])


def delete_source(source_id: str) -> bool:
    r = subprocess.run(
        ["nlm", "source", "delete", source_id, "--confirm"],
        capture_output=True,
        text=True,
    )
    return r.returncode == 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--notebook-id", default=NB_DEFAULT)
    ap.add_argument("--what-if", action="store_true")
    ap.add_argument("--export-titles", action="store_true", help="Write reports/notebooklm_06_source_titles_raw_v1.txt")
    ap.add_argument(
        "--aggressive-review",
        action="store_true",
        help="Also delete review-bucket titles without goldsan/IoT/project hints (see export_notebooklm_06_delete_titles_v1.py).",
    )
    ap.add_argument("--out", default=str(OUT_DEFAULT))
    args = ap.parse_args()

    sources = fetch_sources(args.notebook_id)
    if args.export_titles:
        raw_path = ROOT / "reports" / "notebooklm_06_source_titles_raw_v1.txt"
        lines = ["# NL 06 source titles", f"# count={len(sources)}", ""]
        lines.extend(s.get("title", "") for s in sources if s.get("title"))
        raw_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    to_delete: list[dict] = []
    kept: list[dict] = []
    review_skipped = 0
    for s in sources:
        sid = s.get("id", "")
        title = s.get("title", "")
        base = base_title(title)
        bucket = classify(title, aggressive_review=args.aggressive_review)
        row = {"id": sid, "title": title, "base_title": base, "bucket": bucket}
        if bucket == "delete":
            to_delete.append(row)
        elif bucket == "keep":
            kept.append(row)
        else:
            review_skipped += 1
            kept.append(row)

    policy = "delete_bucket_only; review_not_touched"
    if args.aggressive_review:
        policy = "delete_bucket + aggressive_review (goldsan/IoT hints preserved)"

    doc = {
        "schema": "notebooklm_06_offtopic_prune_result_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "notebook_id": args.notebook_id,
        "policy": policy,
        "sources_before": len(sources),
        "keep_count": len(kept),
        "delete_count": len(to_delete),
        "review_preserved": review_skipped,
        "delete": to_delete,
        "out": str(args.out),
    }

    if args.what_if:
        Path(args.out).write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"what_if": True, "delete_count": len(to_delete), "out": args.out}, ensure_ascii=False))
        return 0

    ok = fail = 0
    for row in to_delete:
        if delete_source(row["id"]):
            ok += 1
        else:
            fail += 1

    sources_after = fetch_sources(args.notebook_id)
    doc["deleted_ok"] = ok
    doc["deleted_fail"] = fail
    doc["sources_after"] = len(sources_after)
    Path(args.out).write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"deleted_ok": ok, "deleted_fail": fail, "sources_after": len(sources_after), "out": args.out},
            ensure_ascii=False,
        )
    )
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
