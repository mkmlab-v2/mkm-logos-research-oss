#!/usr/bin/env python3
"""Print Windows py launcher tag for Python 3.11 (stdout) or exit 1."""
from __future__ import annotations

import subprocess
import sys

TAGS = ("-V:3.11", "-3.11-64", "-3.11", "-V:3.11-64")


def _ok(tag: str) -> bool:
    proc = subprocess.run(
        [
            "py",
            tag,
            "-c",
            "import sys; sys.exit(0 if sys.version_info[:2]==(3,11) else 1)",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode == 0


def main() -> int:
    for tag in TAGS:
        if _ok(tag):
            print(tag, end="")
            return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
