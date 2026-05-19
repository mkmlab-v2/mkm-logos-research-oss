#!/usr/bin/env python3
"""YouTube script / newsletter draft generator v2 — assemble-only, unified queue, no publish."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "docs/final/schemas/marketing_content_queue_v1.schema.json"
DEFAULT_QUEUE = ROOT / "data/marketing/marketing_content_queue.json"
KPI_JSON = ROOT / "reports/constitution/btrack_pilot/ultra_compression_kpi_summary_latest.json"
ENTERPRISE_MD = ROOT / "docs/final/artifacts/compression_enterprise_executive_summary_v1.md"

OUT_DIRS = {
    "youtube_script": ROOT / "reports/marketing/youtube_scripts",
    "newsletter": ROOT / "reports/marketing/newsletter_drafts",
}

BANNED_RE = [
    re.compile(p, re.I)
    for p in [
        r"guaranteed\s+returns?",
        r"100%\s*(cure|lossless|restore)",
        r"hallucination\s+eliminated",
        r"신경과학적으로\s*증명",
        r"수익\s*보장",
    ]
]

DISCLAIMER_EN = (
    "> **[DRAFT]** Not investment advice. Bench metrics artifact-bound. "
    "Not live trading or clinical advice."
)
DISCLAIMER_KO = (
    "> **[DRAFT]** 투자 권유·수익 보장 아님. 벤치 수치는 아티팩트 기준. 실매매·임상 트리거 아님."
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _validate(doc: dict[str, Any]) -> None:
    import jsonschema

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema).validate(doc)


def _kpi_lines() -> list[str]:
    if not KPI_JSON.is_file():
        return ["- KPI: (artifact missing)"]
    doc = _load(KPI_JSON)
    active = doc.get("active_kpi") if isinstance(doc.get("active_kpi"), dict) else {}
    return [
        f"- global_token_saving_rate: {active.get('global_token_saving_rate')}",
        f"- avg_reconstruction_fidelity_jaccard: {active.get('avg_reconstruction_fidelity_jaccard')}",
        f"- source: `{KPI_JSON.relative_to(ROOT).as_posix()}`",
    ]


def _scan_banned(text: str) -> list[str]:
    return [p.pattern for p in BANNED_RE if p.search(text)]


def _assemble_youtube(item: dict[str, Any]) -> str:
    loc = item.get("locale", "en")
    disc = DISCLAIMER_KO if loc == "ko" else DISCLAIMER_EN
    hook = item.get("hook") or item.get("topic", "")
    return "\n".join(
        [
            f"# YouTube script [DRAFT] — {item.get('id')}",
            "",
            disc,
            "",
            f"- **generated_at_utc:** `{_utc_now()}`",
            f"- **mode:** assemble_only",
            f"- **target_length:** ~8–10 min talking head / voiceover",
            "",
            "## Hook (0:00–0:30)",
            hook,
            "",
            "## Act 1 — Problem (platform token spend)",
            str(item.get("topic", "")),
            "",
            "## Act 2 — MKM governed compression (artifact-bound)",
            "Explain deterministic governance vs leaderboard fine-tuning per vertical.",
            "",
            "### KPI (artifact-bound only)",
            *(_kpi_lines()),
            "",
            "## Act 3 — CTA",
            f"Learn more: {item.get('cta_url', 'https://a-codeai.com')}",
            "",
            "## B-roll notes",
            "- Show enterprise summary MD paths only; no fabricated UI metrics.",
            "",
        ]
    )


def _assemble_newsletter(item: dict[str, Any]) -> str:
    loc = item.get("locale", "en")
    disc = DISCLAIMER_KO if loc == "ko" else DISCLAIMER_EN
    subject = f"[DRAFT] {str(item.get('topic', ''))[:72]}"
    return "\n".join(
        [
            f"# Newsletter [DRAFT] — {item.get('id')}",
            "",
            disc,
            "",
            f"- **generated_at_utc:** `{_utc_now()}`",
            f"- **mode:** assemble_only",
            "",
            f"**Subject:** {subject}",
            "",
            "## Opening",
            item.get("hook") or item.get("topic", ""),
            "",
            "## Body",
            str(item.get("topic", "")),
            "",
            "### Metrics (artifact-bound)",
            *(_kpi_lines()),
            "",
            "## Footer",
            f"CTA: {item.get('cta_url', '')}",
            "",
        ]
    )


def _process_item(item: dict[str, Any], channel: str) -> dict[str, Any]:
    out_dir = OUT_DIRS[channel]
    out_dir.mkdir(parents=True, exist_ok=True)
    body = _assemble_youtube(item) if channel == "youtube_script" else _assemble_newsletter(item)
    banned = _scan_banned(body)
    if banned:
        body += "\n\n<!-- BANNED_PATTERN_WARNING: " + ", ".join(banned) + " -->\n"
    md_path = out_dir / f"{item['id']}_{_utc_now()[:10]}_[DRAFT].md"
    md_path.write_text(body, encoding="utf-8")
    return {
        "id": item["id"],
        "status": "drafted",
        "drafted_at_utc": _utc_now(),
        "draft_paths": {"markdown": md_path.relative_to(ROOT).as_posix()},
        "banned_hits": banned,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    ap.add_argument(
        "--channel",
        choices=["youtube_script", "newsletter", "all"],
        default="all",
        help="Which channel items to process",
    )
    ap.add_argument("--item-id", help="Single item id")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not args.queue.is_file():
        print(f"queue missing: {args.queue}", flush=True)
        return 2

    doc = _load(args.queue)
    _validate(doc)
    channels = {"youtube_script", "newsletter"} if args.channel == "all" else {args.channel}

    targets = [
        it
        for it in doc.get("items", [])
        if isinstance(it, dict)
        and it.get("channel") in channels
        and it.get("status") == "pending"
    ]
    if args.item_id:
        targets = [it for it in doc.get("items", []) if it.get("id") == args.item_id]
        if not targets:
            print(f"item not found: {args.item_id}", flush=True)
            return 2

    if not targets:
        print("no pending items for channel(s)")
        return 0

    if args.dry_run:
        print(json.dumps({"ok": True, "would_process": [t.get("id") for t in targets]}))
        return 0

    target_ids = {str(t.get("id")) for t in targets}
    for item in doc.get("items", []):
        if str(item.get("id")) not in target_ids:
            continue
        ch = str(item["channel"])
        if ch not in OUT_DIRS:
            continue
        result = _process_item(item, ch)
        item["status"] = result["status"]
        item["drafted_at_utc"] = result["drafted_at_utc"]
        item["draft_paths"] = result["draft_paths"]
        print(f"drafted: {result['id']} -> {result['draft_paths']['markdown']}")
    doc["updated_at_utc"] = _utc_now()
    _validate(doc)
    args.queue.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
