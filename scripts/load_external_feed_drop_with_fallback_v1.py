#!/usr/bin/env python3
"""Validate external_feed_drop_v1 and emit validated copy + status JSON."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FALLBACK = ROOT / "docs/final/artifacts/external_feed_drop_latest.validated.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    return doc if isinstance(doc, dict) else None


def _validate_doc(doc: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if doc.get("schema") != "external_feed_drop_v1":
        errors.append("schema must be external_feed_drop_v1")
    data = doc.get("data")
    if not isinstance(data, list):
        errors.append("data must be a list")
    elif not data:
        errors.append("data is empty")
    else:
        for i, row in enumerate(data[:5]):
            if not isinstance(row, dict):
                errors.append(f"data[{i}] must be object")
                continue
            if not str(row.get("title") or row.get("headline") or "").strip():
                errors.append(f"data[{i}] missing title/headline")
    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description="external_feed_drop validate + fallback")
    ap.add_argument("--latest", type=str, default="docs/final/artifacts/external_feed_drop_latest.json")
    ap.add_argument("--output", type=str, default="docs/final/artifacts/external_feed_drop_latest.validated.json")
    ap.add_argument("--status-output", type=str, default="docs/final/artifacts/external_feed_drop_validation_status_latest.json")
    ap.add_argument("--fallback", type=Path, default=DEFAULT_FALLBACK)
    ap.add_argument("--allow-empty", action="store_true", help="Accept empty data as degraded (exit 0).")
    args = ap.parse_args()

    latest_path = (ROOT / args.latest).resolve()
    out_path = (ROOT / args.output).resolve()
    status_path = (ROOT / args.status_output).resolve()

    doc = _load(latest_path)
    used_fallback = False
    if doc is None:
        doc = _load(args.fallback.resolve())
        used_fallback = doc is not None

    errors: list[str] = []
    if doc is None:
        errors.append("no latest or fallback feed document")
        mode = "missing"
        degraded = True
    else:
        errors = _validate_doc(doc)
        items = doc.get("data") if isinstance(doc.get("data"), list) else []
        if errors and not used_fallback:
            fb = _load(args.fallback.resolve())
            if fb and _validate_doc(fb) == []:
                doc = fb
                used_fallback = True
                errors = []
        mode = "ok" if not errors else "degraded"
        degraded = bool(errors) or not items

    if errors and not args.allow_empty:
        exit_code = 1
    elif degraded and not args.allow_empty and not (doc and doc.get("data")):
        exit_code = 1
    else:
        exit_code = 0

    if doc is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    status = {
        "schema": "external_feed_drop_validation_status_v1",
        "generated_at_utc": _utc_now(),
        "mode": mode,
        "latest_mode": mode,
        "degraded": degraded,
        "used_fallback": used_fallback,
        "items_count": len(doc.get("data") or []) if doc else 0,
        "errors": errors[:32],
        "paths": {
            "latest": str(latest_path).replace("\\", "/"),
            "validated": str(out_path).replace("\\", "/"),
        },
        "research_only": True,
    }
    status_path.parent.mkdir(parents=True, exist_ok=True)
    status_path.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": exit_code == 0, "mode": mode, "degraded": degraded, "items_count": status["items_count"]}, ensure_ascii=False))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
