#!/usr/bin/env python3
"""After live LinkedIn post: mark-published + refresh handoff (supports chat triggers)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/marketing/marketing_linkedin_publish_closure_latest.json"

# Chat phrases → item id (partial match on commander message)
TRIGGER_MAP = {
    "showroom": "showroom_topology_observability_ko",
    "topology": "showroom_topology_observability_ko",
    "compression": "compression_governance_moat_w12",
    "moat": "compression_governance_moat_w12",
}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_mark_published(item_id: str) -> dict[str, Any]:
    proc = subprocess.run(
        [sys.executable, "scripts/set_marketing_queue_publish_status_v1.py", "--item-id", item_id, "--mark-published"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    out = (proc.stdout or "").strip()
    try:
        parsed = json.loads(out) if out.startswith("{") else {"raw": out}
    except json.JSONDecodeError:
        parsed = {"raw": out}
    return {
        "item_id": item_id,
        "exit_code": int(proc.returncode),
        "ok": proc.returncode == 0,
        "result": parsed,
    }


def _resolve_from_phrase(phrase: str) -> list[str]:
    low = phrase.lower()
    if "올렸" in phrase or "posted" in low or "published" in low:
        if "compression" in low or "moat" in low or "영문" in phrase:
            return ["compression_governance_moat_w12"]
        if "showroom" in low or "topology" in low or "한국" in phrase or "ko" in low:
            return ["showroom_topology_observability_ko"]
        return ["showroom_topology_observability_ko", "compression_governance_moat_w12"]
    ids: list[str] = []
    for key, iid in TRIGGER_MAP.items():
        if key in low:
            ids.append(iid)
    return list(dict.fromkeys(ids))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--item-id", action="append", default=[], help="Repeatable queue item id")
    ap.add_argument("--phrase", default="", help="Commander chat e.g. 올렸어 / showroom 올렸어")
    ap.add_argument("--all-human-approved", action="store_true", help="Mark all human_approved linkedin items")
    ap.add_argument("--refresh-handoff", action="store_true", default=True)
    ap.add_argument("--no-refresh-handoff", action="store_false", dest="refresh_handoff")
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    ids: list[str] = list(args.item_id)
    if args.phrase:
        ids.extend(_resolve_from_phrase(args.phrase))
    if args.all_human_approved:
        qpath = ROOT / "data/marketing/marketing_content_queue.json"
        if qpath.is_file():
            q = json.loads(qpath.read_text(encoding="utf-8"))
            for row in q.get("items") or []:
                if isinstance(row, dict) and row.get("channel") == "linkedin":
                    if row.get("status") == "human_approved":
                        ids.append(str(row.get("id") or ""))
    ids = [i for i in dict.fromkeys(ids) if i]

    if not ids:
        print(json.dumps({"ok": False, "error": "no_item_ids"}, ensure_ascii=False))
        return 2

    results = [_run_mark_published(iid) for iid in ids]
    if args.refresh_handoff:
        subprocess.run(
            [sys.executable, "scripts/build_marketing_publish_handoff_v1.py"],
            cwd=str(ROOT),
            check=False,
        )

    doc = {
        "schema": "marketing_linkedin_publish_closure_v1",
        "generated_at_utc": _utc(),
        "marked": results,
        "all_ok": all(r["ok"] for r in results),
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["all_ok"], "output": str(args.out_json), "items": ids}, ensure_ascii=False))
    return 0 if doc["all_ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
