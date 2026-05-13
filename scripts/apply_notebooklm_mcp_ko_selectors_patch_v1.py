#!/usr/bin/env python3
"""
Idempotently patch global notebooklm-mcp dist/notebooklm/selectors.js for:

  1) Korean NotebookLM UI (add source / pasted text / insert buttons)
  2) Emoji false positives on [role=dialog]: exclude emoji-keyboard classes and
     emoji palette aria-label fragments (KO/EN) when classes are missing on the node.

Upstream 2.0.0 omits (1); Playwright matches hidden emoji role=dialog first for (2).

Target (default): %APPDATA%/npm/node_modules/notebooklm-mcp/dist/notebooklm/selectors.js

After ANY change: Developer: Reload Window (or MCP notebooklm toggle) + NEW chat.
Re-run after: npm i -g notebooklm-mcp@<version>
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def _patch_ko_buttons(raw: str) -> tuple[str, bool]:
    if "소스 추가" in raw:
        return raw, False
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
    changed = False
    for label, old, new in (
        ("addButton", old_add, new_add),
        ("sourceTypeText", old_text, new_text),
        ("insertConfirm", old_ins, new_ins),
    ):
        if old not in raw:
            raise ValueError(f"anchor not found for {label} — notebooklm-mcp version changed?")
        raw = raw.replace(old, new, 1)
        changed = True
    return raw, changed


def _patch_overlay_excludes_emoji(raw: str) -> tuple[str, bool]:
    """Exclude emoji pickers: class-based + aria-label (KO/EN) fragments."""
    needle_aria = ':not([aria-label*="팔레트"])'
    if needle_aria in raw and raw.count(needle_aria) >= 3:
        return raw, False
    needle_cls = ':not(.emoji-keyboard__container):not([class*="emoji-keyboard__"])'
    # All three selectors must carry the exclude (vanilla omits; partial MKM may fix only overlayPane).
    if needle_aria not in raw and needle_cls in raw and raw.count(needle_cls) >= 3:
        # Upgrade class-only MKM overlay lines → class + aria-label excludes.
        old_triple = """        overlayPane: '[role="dialog"]:not(.emoji-keyboard__container):not([class*="emoji-keyboard__"])',
        overlayInput: '[role="dialog"]:not(.emoji-keyboard__container):not([class*="emoji-keyboard__"]) input[type="text"]:not([readonly])',
        overlayTextarea: '[role="dialog"]:not(.emoji-keyboard__container):not([class*="emoji-keyboard__"]) textarea',"""
        new_triple = """        overlayPane:
            '[role="dialog"]:not(.emoji-keyboard__container):not([class*="emoji-keyboard__"]):not([aria-label*="팔레트"]):not([aria-label*="이모티콘"]):not([aria-label*="palette" i]):not([aria-label*="emoji" i])',
        overlayInput:
            '[role="dialog"]:not(.emoji-keyboard__container):not([class*="emoji-keyboard__"]):not([aria-label*="팔레트"]):not([aria-label*="이모티콘"]):not([aria-label*="palette" i]):not([aria-label*="emoji" i]) input[type="text"]:not([readonly])',
        overlayTextarea:
            '[role="dialog"]:not(.emoji-keyboard__container):not([class*="emoji-keyboard__"]):not([aria-label*="팔레트"]):not([aria-label*="이모티콘"]):not([aria-label*="palette" i]):not([aria-label*="emoji" i]) textarea',"""
        if old_triple in raw:
            return raw.replace(old_triple, new_triple, 1), True
        old_ml = """        overlayPane:
            '[role="dialog"]:not(.emoji-keyboard__container):not([class*="emoji-keyboard__"])',
        overlayInput:
            '[role="dialog"]:not(.emoji-keyboard__container):not([class*="emoji-keyboard__"]) input[type="text"]:not([readonly])',
        overlayTextarea:
            '[role="dialog"]:not(.emoji-keyboard__container):not([class*="emoji-keyboard__"]) textarea',"""
        if old_ml in raw:
            return raw.replace(old_ml, new_triple, 1), True
    if raw.count(needle_cls) >= 3 and needle_aria in raw:
        return raw, False
    # Vanilla: three consecutive lines
    old_block = """        overlayPane: '[role="dialog"]',
        overlayInput: '[role="dialog"] input[type="text"]:not([readonly])',
        overlayTextarea: '[role="dialog"] textarea',"""
    new_block = """        /**
         * Real Material modal. `[role="dialog"]` alone matches hidden emoji
         * keyboards (e.g. aria-label="이모티콘 문자 팔레트") — exclude by class and
         * aria-label (some builds omit emoji-keyboard__* classes on the dialog node).
         */
        overlayPane:
            '[role="dialog"]:not(.emoji-keyboard__container):not([class*="emoji-keyboard__"]):not([aria-label*="팔레트"]):not([aria-label*="이모티콘"]):not([aria-label*="palette" i]):not([aria-label*="emoji" i])',
        overlayInput:
            '[role="dialog"]:not(.emoji-keyboard__container):not([class*="emoji-keyboard__"]):not([aria-label*="팔레트"]):not([aria-label*="이모티콘"]):not([aria-label*="palette" i]):not([aria-label*="emoji" i]) input[type="text"]:not([readonly])',
        overlayTextarea:
            '[role="dialog"]:not(.emoji-keyboard__container):not([class*="emoji-keyboard__"]):not([aria-label*="팔레트"]):not([aria-label*="이모티콘"]):not([aria-label*="palette" i]):not([aria-label*="emoji" i]) textarea',"""
    if old_block in raw:
        return raw.replace(old_block, new_block, 1), True
    # Older MKM: overlayPane-only comment variant (single-line overlayPane already patched)
    old_in = "        overlayInput: '[role=\"dialog\"] input[type=\"text\"]:not([readonly])',"
    new_in = "        overlayInput: '[role=\"dialog\"]:not(.emoji-keyboard__container):not([class*=\"emoji-keyboard__\"]) input[type=\"text\"]:not([readonly])',"
    old_ta = "        overlayTextarea: '[role=\"dialog\"] textarea',"
    new_ta = "        overlayTextarea: '[role=\"dialog\"]:not(.emoji-keyboard__container):not([class*=\"emoji-keyboard__\"]) textarea',"
    changed = False
    if old_in in raw:
        raw = raw.replace(old_in, new_in, 1)
        changed = True
    if old_ta in raw:
        raw = raw.replace(old_ta, new_ta, 1)
        changed = True
    if changed:
        return raw, True
    raise ValueError("overlayPane patch anchor not found — selectors.js layout changed?")


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
    out = raw
    any_change = False
    try:
        out, c1 = _patch_ko_buttons(out)
        any_change = any_change or c1
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    try:
        out, c2 = _patch_overlay_excludes_emoji(out)
        any_change = any_change or c2
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    if not any_change:
        print(f"OK: nothing to do ({path})")
    else:
        path.write_text(out, encoding="utf-8")
        print(f"OK: patched {path}")
    print("Next: Reload Window (or MCP notebooklm toggle) then NEW chat; retry add_source.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
