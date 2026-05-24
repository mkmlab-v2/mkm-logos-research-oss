#!/usr/bin/env python3
"""Sync ms_rq019_paste_ready Track A bench KPI strings to 41658 refreeze (49.1% / 0.873)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PASTE_DIR = ROOT / "reports" / "ms_rq019_paste_ready"

# Order matters: longer / more specific first.
_REPLACEMENTS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"약 47\.5%·Jaccard 약 0\.890\(본선 동결\)"), "약 49.1%·Jaccard 약 0.873(41658 lexicon SSOT · 2026-05-23)"),
    (re.compile(r"약 47\.5%·Jaccard 약 0\.890"), "약 49.1%·Jaccard 약 0.873"),
    (re.compile(r"token saving 약 47\.5%, reconstruction Jaccard 약 0\.890"), "token saving 약 49.1%, reconstruction Jaccard 약 0.873"),
    (re.compile(r"economy 약 47\.5%·Jaccard 약 0\.890"), "economy 약 49.1%·Jaccard 약 0.873"),
    (re.compile(r"토큰 절감 약 47\.5%, Jaccard 복원 프록시 약 0\.890"), "토큰 절감 약 49.1%, Jaccard 복원 프록시 약 0.873"),
    (re.compile(r"글로벌 토큰 절감률 평균 47\.5%"), "글로벌 토큰 절감률 평균 49.1%"),
    (re.compile(r"47\.5% 벤치"), "49.1% 벤치"),
    (re.compile(r"KPI 47\.5% 동결"), "KPI 49.1% 동결(41658)"),
    (re.compile(r"벤치 47\.5%를"), "벤치 49.1%를"),
    (re.compile(r"47\.5%·0\.890만"), "49.1%·0.873만"),
    (re.compile(r"47\.5%·COMP-4D"), "49.1%·COMP-4D"),
    (re.compile(r"47\.5%"), "49.1%"),
    (re.compile(r"0\.890"), "0.873"),
]


def main() -> int:
    if not PASTE_DIR.is_dir():
        print(f"ERROR: missing {PASTE_DIR}", file=sys.stderr)
        return 2
    changed: list[str] = []
    for path in sorted(PASTE_DIR.glob("*.txt")):
        text = path.read_text(encoding="utf-8")
        new = text
        for pat, repl in _REPLACEMENTS:
            new = pat.sub(repl, new)
        if new != text:
            path.write_text(new, encoding="utf-8")
            changed.append(path.name)
    print(json_dumps({"ok": True, "changed_files": changed, "count": len(changed)}))
    return 0


def json_dumps(obj: object) -> str:
    import json

    return json.dumps(obj, ensure_ascii=False)


if __name__ == "__main__":
    raise SystemExit(main())
