#!/usr/bin/env python3
"""Minimal prophecy × micro-codebook PoC — writes audit JSON (research rail)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "prophecy_micro_codebook_poc_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    out = args.out if args.out.is_absolute() else (ROOT / args.out)
    doc = {
        "schema": "prophecy_micro_codebook_poc_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "status": "ok",
        "note": "Placeholder PoC: dual-track codebook path smoke; expand with real prophecy join when scoped.",
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
