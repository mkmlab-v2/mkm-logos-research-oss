#!/usr/bin/env python3
"""Smoke: investor deck KO skeleton must not contain digestion-blocked hero numerics."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DECK = ROOT / "docs/research/MKM_UNIVERSAL_ROOT_INVESTOR_DECK_SKELETON_KO_V1.md"
DEFAULT_BLOCKED = ROOT / "docs/final/artifacts/mkm_digestion_blocked_public_claims_latest.json"
DEFAULT_OUT = ROOT / "reports/investor_deck_digestion_firewall_check_latest.json"

FORBIDDEN_IN_HERO = (
    re.compile(r"\b96\.8\s*%"),
    re.compile(r"\b94\.2\s*%"),
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    parser = argparse.ArgumentParser(description="Investor deck digestion firewall smoke")
    parser.add_argument("--deck", type=Path, default=DEFAULT_DECK)
    parser.add_argument("--blocked", type=Path, default=DEFAULT_BLOCKED)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    deck_path = args.deck.resolve()
    if not deck_path.is_file():
        print(json.dumps({"ok": False, "error": f"missing deck: {deck_path}"}, ensure_ascii=False))
        return 2

    text = deck_path.read_text(encoding="utf-8")
    # Scan body only — Slide 17 checklist may mention blocked numerics by design.
    if "## Slide 17" in text:
        text = text.split("## Slide 17", 1)[0]

    hits: list[dict[str, str]] = []
    for pattern in FORBIDDEN_IN_HERO:
        for match in pattern.finditer(text):
            hits.append({"pattern": pattern.pattern, "match": match.group(0)})

    has_slide17_check = "96.8%" in text and "blocked" in text.lower() or "Digestion" in text
    ok = len(hits) == 0

    report = {
        "schema": "investor_deck_digestion_firewall_check_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "ok": ok,
        "forbidden_numeric_hits": hits,
        "slide17_digestion_check_present": has_slide17_check,
        "deck_path": str(deck_path).replace("\\", "/"),
        "send_gate": "HOLD",
        "research_only": True,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "forbidden_hits": len(hits)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
