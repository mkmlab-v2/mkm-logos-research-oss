#!/usr/bin/env python3
"""Scan 창업패키지 AI graft/paste for forbidden phrases."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GRAFT = ROOT / "docs/final/artifacts/startup_package_ai_2026_submission_graft_v1.md"
PASTE_DIR = ROOT / "reports/kstartup_startup_package_ai_paste_ready"
OUT = ROOT / "reports/kstartup_startup_package_ai_forbidden_scan_latest.json"

SKIP = {"plan_disclaimer_paste.txt", "00_paste_order.txt"}

AFFIRMATIVE = [
    (r"무조건\s*당선", "무조건 당선"),
    (r"47\.5\s*%|47\s*%", "압축 47% 헤드라인"),
    (r"Track\s*A\s*실매매|자동\s*매매", "실매매"),
    (r"무손실|100\s*%\s*제거", "무손실·100%"),
    (r"수익\s*보장|투자\s*수익", "수익 보장"),
    (r"LG\s*압축\s*OEM", "LG OEM"),
    (r"적중률\s*\d|승률\s*\d", "적중률·승률"),
]

DENIAL = ("금지", "제외", "단정", "보장하지", "아님", "PoC", "안)", "면책", "DRAFT")


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _scan_text(text: str, fname: str) -> list[dict]:
    hits: list[dict] = []
    for pat, label in AFFIRMATIVE:
        for m in re.finditer(pat, text, re.IGNORECASE):
            win = text[max(0, m.start() - 80) : m.end() + 80]
            if any(d in win for d in DENIAL):
                continue
            hits.append({"file": fname, "label": label, "snippet": win.replace("\n", " ")[:120]})
    return hits


def main() -> int:
    paths = [GRAFT] if GRAFT.is_file() else []
    if PASTE_DIR.is_dir():
        paths.extend(sorted(PASTE_DIR.glob("*.txt")))
    all_hits: list[dict] = []
    for p in paths:
        if p.name in SKIP:
            continue
        all_hits.extend(_scan_text(p.read_text(encoding="utf-8"), p.name))

    ok = len(all_hits) == 0
    OUT.write_text(
        json.dumps(
            {
                "schema": "kstartup_startup_package_ai_forbidden_scan_v1",
                "generated_at_utc": _utc(),
                "pass": ok,
                "hits": all_hits,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(str(OUT))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
