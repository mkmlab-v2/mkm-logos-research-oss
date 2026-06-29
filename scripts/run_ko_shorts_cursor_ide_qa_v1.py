#!/usr/bin/env python3
"""Run Cursor IDE automated QA for ko shorts burn-in [HYPO]."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ko_shorts_cursor_ide_qa_lib_v1 import (  # noqa: E402
    DEFAULT_PORT,
    PROFILE_NETFLIX_V16,
    build_cursor_ide_qa_report_v1,
)

DEFAULT_OUT = ROOT / "reports/ko_shorts_cursor_ide_qa_v1_latest.json"


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--profile", default=PROFILE_NETFLIX_V16)
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = ap.parse_args()

    report = build_cursor_ide_qa_report_v1(profile_key=args.profile, port=args.port)
    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": report["auto_pass"],
                "out": _rel(out),
                "preview_url": report["preview_url"],
                "auto_pass_case_count": report["auto_pass_case_count"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["auto_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
