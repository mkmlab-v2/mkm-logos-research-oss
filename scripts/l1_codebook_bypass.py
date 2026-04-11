#!/usr/bin/env python3
"""L1 literal slotting + codebook restore (research PoC; used by run_l1_codebook_bypass_bench.py)."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_POC_OUT = ROOT / "docs" / "final" / "artifacts" / "l1_codebook_bypass_poc_latest.json"


@dataclass(frozen=True)
class Slot:
    slot_id: str
    value: str


def _patterns() -> list[re.Pattern[str]]:
    return [
        re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[A-Za-z]{2,}"),
        re.compile(r"\bREQ_[A-Za-z0-9_]+\b"),
        re.compile(r"\bTXN_[A-Za-z0-9]+\b"),
        re.compile(r"BTCUSDT"),
        re.compile(r"\bMKM_MAIN_[A-Za-z0-9_]+\b"),
        re.compile(r"FollowUpCase_\d+"),
        re.compile(r"DrKim"),
        re.compile(r"\bA\d+\b"),
        re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}Z"),
        re.compile(r"\b\d{4}-\d{2}-\d{2}\b"),
        re.compile(r"\b\d+\.\d+\b"),
        re.compile(r"\b\d{2}:\d{2}\b"),
    ]


def extract_literals(text: str) -> tuple[str, list[Slot]]:
    spans: list[tuple[int, int, str]] = []
    for rx in _patterns():
        for m in rx.finditer(text):
            spans.append((m.start(), m.end(), m.group(0)))
    spans.sort(key=lambda t: (t[0], -(t[1] - t[0])))
    picked: list[tuple[int, int, str]] = []
    for start, end, val in spans:
        if any(not (end <= ps or start >= pe) for ps, pe, _ in picked):
            continue
        picked.append((start, end, val))
    picked.sort(key=lambda t: t[0])

    slots: list[Slot] = []
    out: list[str] = []
    pos = 0
    for i, (start, end, val) in enumerate(picked, start=1):
        sid = "{{L1_SLOT_%03d}}" % i
        out.append(text[pos:start])
        out.append(sid)
        slots.append(Slot(slot_id=sid, value=val))
        pos = end
    out.append(text[pos:])
    return "".join(out), slots


def build_codebook(slots: list[Slot]) -> dict[str, str]:
    return {s.slot_id: s.value for s in slots}


def restore_from_codebook(masked_text: str, codebook: dict[str, str]) -> str:
    s = masked_text
    for sid, val in codebook.items():
        s = s.replace(sid, val)
    return s


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _poc_payload() -> dict[str, Any]:
    sample = "Patient ID A123 visited on 2026-04-09 with glucose 128.5 and email ops@example.com"
    masked, slots = extract_literals(sample)
    cb = build_codebook(slots)
    restored = restore_from_codebook(masked, cb)
    return {
        "schema": "l1_codebook_bypass_poc_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "sample": sample,
        "masked_preview": masked[:200],
        "restored_ok": restored == sample,
        "slot_count": len(slots),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="L1 codebook bypass PoC (writes artifact JSON).")
    ap.add_argument("--out", type=Path, default=DEFAULT_POC_OUT)
    args = ap.parse_args()
    out = args.out if args.out.is_absolute() else (ROOT / args.out)
    doc = _poc_payload()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
