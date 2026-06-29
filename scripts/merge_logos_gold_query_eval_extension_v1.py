#!/usr/bin/env python3
"""Merge logos_gold_query_eval extension pack into main fixture (12→24) [HYPO]."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GOLD = ROOT / "docs/final/fixtures/logos_gold_query_eval_v1.json"
DEFAULT_EXT = ROOT / "docs/final/fixtures/logos_gold_query_eval_extension_v1.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def merge_gold(
    base: dict[str, Any],
    ext: dict[str, Any],
    *,
    extension_path: Path | None = None,
) -> dict[str, Any]:
    base_items = [x for x in (base.get("items") or []) if isinstance(x, dict)]
    ext_items = [x for x in (ext.get("items") or []) if isinstance(x, dict)]
    seen = {str(x.get("id")) for x in base_items}
    merged = list(base_items)
    added = 0
    for item in ext_items:
        qid = str(item.get("id") or "")
        if not qid or qid in seen:
            continue
        merged.append(item)
        seen.add(qid)
        added += 1
    out = dict(base)
    ext_name = extension_path.name if isinstance(extension_path, Path) else str(extension_path)
    if "extension_v2" in ext_name:
        out["version"] = "1.2.0"
    elif "extension_v1" in ext_name or ext.get("schema", "").endswith("extension_v1"):
        out["version"] = "1.1.0"
    else:
        out["version"] = ext.get("target_gold_version") or base.get("version") or "1.2.0"
    out["merged_at_utc"] = _utc_now()
    out["extension_source"] = extension_path.as_posix() if isinstance(extension_path, Path) else str(extension_path)
    out["items"] = merged
    out["item_count"] = len(merged)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gold-json", type=Path, default=DEFAULT_GOLD)
    ap.add_argument("--extension-json", type=Path, default=DEFAULT_EXT)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not args.gold_json.is_file():
        print(f"[ERROR] missing {args.gold_json}", file=__import__("sys").stderr)
        return 2
    if not args.extension_json.is_file():
        print(f"[ERROR] missing {args.extension_json}", file=__import__("sys").stderr)
        return 2

    base = _read(args.gold_json)
    ext = _read(args.extension_json)
    merged = merge_gold(base, ext, extension_path=args.extension_json)
    if args.dry_run:
        print(json.dumps({"ok": True, "item_count": merged["item_count"], "dry_run": True}, ensure_ascii=False))
        return 0

    args.gold_json.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"ok": True, "item_count": merged["item_count"], "out": str(args.gold_json)},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
