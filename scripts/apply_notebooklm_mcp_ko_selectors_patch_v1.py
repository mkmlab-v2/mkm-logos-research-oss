#!/usr/bin/env python3
"""
Idempotently extend global notebooklm-mcp selectors.js for Korean NotebookLM UI.

Fixes add_source failing with: Could not open the "Add source" dialog
when the MCP automation profile uses Korean UI (missing aria-label / button text).

Target (default): %APPDATA%/npm/node_modules/notebooklm-mcp/dist/notebooklm/selectors.js

After success: Reload Cursor Window (or MCP notebooklm toggle) + NEW chat.
Re-run after: npm i -g notebooklm-mcp@<version>
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def main() -> int:
    appdata = os.environ.get("APPDATA", "")
    if not appdata:
        print("ERROR: APPDATA not set", file=sys.stderr)
        return 1
    default = Path(appdata) / "npm/node_modules/notebooklm-mcp/dist/notebooklm/selectors.js"
    path = Path(os.environ.get("NOTEBOOKLM_SELECTORS_JS", str(default))).resolve()
    if not path.is_file():
        print(f"ERROR: missing {path}", file=sys.stderr)
        return 1

    raw = path.read_text(encoding="utf-8")
    if "소스 추가" in raw:
        print(f"OK: already patched ({path})")
        return 0

    old_add = """            'button[aria-label*="\u30bd\u30fc\u30b9\u3092\u8ffd\u52a0" i]',
        ],"""
    new_add = """            'button[aria-label*="\u30bd\u30fc\u30b9\u3092\u8ffd\u52a0" i]',
            // Korean (ko) — NotebookLM UI in Korean uses different aria-labels.
            'button[aria-label*="\uc18c\uc2a4 \ucd94\uac00" i]',
            'button[aria-label*="\uc6d0\ubcf8 \ucd94\uac00" i]',
            'button[aria-label*="\ucd9c\ucc98 \ucd94\uac00" i]',
        ],"""

    old_text = """            'button.drop-zone-icon-button:has-text("\u30b3\u30d4\u30fc\u3057\u305f\u30c6\u30ad\u30b9\u30c8")',
            'span:has-text("Copied text")',"""
    new_text = """            'button.drop-zone-icon-button:has-text("\u30b3\u30d4\u30fc\u3057\u305f\u30c6\u30ad\u30b9\u30c8")',
            'button.drop-zone-icon-button:has-text("\ubd99\uc5ec\ub123\uc740 \ud14d\uc2a4\ud2b8")',
            'button.drop-zone-icon-button:has-text("\ubcf5\uc0ac\ud55c \ud14d\uc2a4\ud2b8")',
            'button.drop-zone-icon-button:has-text("\ubcf5\uc0ac\ub41c \ud14d\uc2a4\ud2b8")',
            'span:has-text("Copied text")',"""

    old_ins = """            'button:has-text("\u8ffd\u52a0")',
            'button:has-text("Add")',"""
    new_ins = """            'button:has-text("\u8ffd\u52a0")',
            'button.mdc-button--raised:has-text("\uc0bd\uc785")',
            'button.mdc-button--raised:has-text("\ucd94\uac00")',
            'button.mat-flat-button:has-text("\uc0bd\uc785")',
            'button.mat-flat-button:has-text("\ucd94\uac00")',
            'button:has-text("\uc0bd\uc785")',
            'button:has-text("\ucd94\uac00")',
            'button:has-text("Add")',"""

    for label, old, new in (
        ("addButton", old_add, new_add),
        ("sourceTypeText", old_text, new_text),
        ("insertConfirm", old_ins, new_ins),
    ):
        if old not in raw:
            print(f"ERROR: anchor not found for {label} — notebooklm-mcp version changed?", file=sys.stderr)
            return 1
        raw = raw.replace(old, new, 1)

    path.write_text(raw, encoding="utf-8")
    print(f"OK: patched {path}")
    print("Next: Reload Window (or MCP notebooklm toggle) then NEW chat; retry add_source.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
