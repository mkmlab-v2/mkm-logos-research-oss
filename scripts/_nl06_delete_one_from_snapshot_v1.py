"""Find refs to delete one NL source from latest snapshot log."""
from __future__ import annotations

import re
import sys
from pathlib import Path


def find_more_ref(lines: list[str], title_substr: str) -> str | None:
    for i, line in enumerate(lines):
        if line.strip().startswith("name:") and title_substr in line and "더보기" not in line:
            for j in range(i + 1, min(i + 8, len(lines))):
                if "name: 더보기" in lines[j]:
                    for k in range(j, min(j + 4, len(lines))):
                        m = re.search(r"ref: (e\d+)", lines[k])
                        if m:
                            return m.group(1)
    return None


def find_menu_delete(lines: list[str]) -> str | None:
    for i, line in enumerate(lines):
        if "role: menuitem" in line:
            for j in range(i, min(i + 4, len(lines))):
                if "name: 소스 삭제" in lines[j]:
                    for k in range(j, min(j + 4, len(lines))):
                        m = re.search(r"ref: (e\d+)", lines[k])
                        if m:
                            return m.group(1)
    return None


def find_confirm_delete(lines: list[str]) -> str | None:
    for i, line in enumerate(lines):
        if line.strip() == "- role: button" or "role: button" in line:
            for j in range(i, min(i + 5, len(lines))):
                if re.match(r"\s+name: 삭제\s*$", lines[j]):
                    for k in range(j, min(j + 4, len(lines))):
                        m = re.search(r"ref: (e\d+)", lines[k])
                        if m:
                            return m.group(1)
    return None


def main() -> int:
    mode = sys.argv[1]
    snap = Path(sys.argv[2]).read_text(encoding="utf-8")
    lines = snap.splitlines()
    if mode == "more":
        ref = find_more_ref(lines, sys.argv[3])
    elif mode == "menu":
        ref = find_menu_delete(lines)
    elif mode == "confirm":
        ref = find_confirm_delete(lines)
    else:
        print("bad mode", file=sys.stderr)
        return 2
    if ref:
        print(ref)
        return 0
    print("NOT_FOUND", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
