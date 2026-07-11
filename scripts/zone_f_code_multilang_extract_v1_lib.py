"""Multilang code-snippet detection for zone_f_code extract pipeline v1.

research_only · extends Python-centric CODE_LINE_START with native fence languages.
"""

from __future__ import annotations

import re

PYTHON_LINE_START = re.compile(
    r"^\s*(def |class |import |from |async def |@app\.|@pytest|try:|except |if __name__)",
    re.MULTILINE,
)

MULTILANG_LINE_START: dict[str, re.Pattern[str]] = {
    "python": PYTHON_LINE_START,
    "typescript": re.compile(
        r"^\s*(export |import |async function|interface |type |const |declare )",
        re.MULTILINE,
    ),
    "javascript": re.compile(
        r"^\s*(export |import |async function|function |const |class )",
        re.MULTILINE,
    ),
    "solidity": re.compile(
        r"^\s*(pragma |contract |function |modifier |mapping|event |struct )",
        re.MULTILINE,
    ),
    "haskell": re.compile(r"^(module |import |\w+\s*::)", re.MULTILINE),
    "clojure": re.compile(r"^\s*(\(ns |\(defn )", re.MULTILINE),
    "dart": re.compile(r"^\s*(Future<|class |void |async |import )", re.MULTILINE),
    "ocaml": re.compile(r"^\s*(let |module |open |type )", re.MULTILINE),
    "fsharp": re.compile(r"^\s*(let |module |open |type )", re.MULTILINE),
    "lua": re.compile(r"^\s*(local function|function )", re.MULTILINE),
    "perl": re.compile(r"^\s*(package |sub )", re.MULTILINE),
    "r": re.compile(r"^\s*(\w+\s*<-|function\s*\()", re.MULTILINE),
    "php": re.compile(r"^\s*(<\?php|namespace |class |function )", re.MULTILINE),
    "swift": re.compile(r"^\s*(struct |class |func |import )", re.MULTILINE),
    "cobol": re.compile(r"^\s+(IDENTIFICATION|PROGRAM-ID|PROCEDURE)", re.MULTILINE),
    "powershell": re.compile(r"^\s*(function |param\()", re.MULTILINE),
}

FENCE_LANG_RE = re.compile(r"```(\w+)")


def detect_fence_lang(text: str) -> str | None:
    m = FENCE_LANG_RE.search(text)
    if not m:
        return None
    lang = m.group(1).lower()
    if lang in ("ts", "tsx"):
        return "typescript"
    if lang in ("js", "jsx"):
        return "javascript"
    return lang


def looks_like_code_snippet(text: str, *, lang: str | None = None) -> bool:
    stripped = text.strip()
    if not stripped or len(stripped) < 20:
        return False

    try_langs: list[str] = []
    if lang:
        try_langs.append(lang)
    try_langs.extend(
        [
            "python",
            "typescript",
            "javascript",
            "solidity",
            "haskell",
            "clojure",
            "dart",
            "ocaml",
            "fsharp",
            "lua",
            "perl",
            "r",
            "php",
            "swift",
            "cobol",
            "powershell",
        ]
    )
    seen: set[str] = set()
    for key in try_langs:
        if key in seen:
            continue
        seen.add(key)
        pat = MULTILANG_LINE_START.get(key)
        if pat and pat.search(stripped):
            return True

    code_markers = ("->", "):", "({", "[]", "{}", "==", "!=", ".json", "/v2/", "=>", ";;")
    hits = sum(1 for m in code_markers if m in stripped)
    return hits >= 2 and ("\n" in stripped or ";" in stripped)


def infer_snippet_language(snippet: str, blob: str) -> str:
    fence = detect_fence_lang(blob)
    if fence:
        return fence
    lower = snippet.lower()
    if "export async function" in snippet or "export function" in snippet:
        return "typescript"
    if "import type" in snippet or "import {" in snippet and " from " in snippet:
        return "typescript"
    if re.search(r":\s*(string|number|boolean|Record<)", snippet):
        return "typescript"
    if "pragma solidity" in lower:
        return "solidity"
    if lower.startswith("module ") or "::" in snippet:
        return "haskell"
    if "(ns " in snippet or "(defn " in snippet:
        return "clojure"
    if "Future<" in snippet:
        return "dart"
    if "local function" in lower:
        return "lua"
    if lower.startswith("package ") and "sub " in lower:
        return "perl"
    if "<-" in snippet and "function" in lower:
        return "r"
    return "python"
