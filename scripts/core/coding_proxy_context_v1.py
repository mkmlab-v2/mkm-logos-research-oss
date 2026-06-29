"""Coding proxy: preserve structured agent blocks (Constraints/Files/Verify) lossless."""
from __future__ import annotations

import re
from typing import Any

_STRUCTURED_MARKERS = ("Constraints:", "Files:", "Verify with")
_MARKER_RE = re.compile(
    r"(Constraints:|Files:|Verify with:?)",
    re.IGNORECASE,
)


def partition_coding_text(text: str) -> tuple[str, list[str]]:
    """Split task body (compressible) vs structured lines (lossless preserve)."""
    matches = list(_MARKER_RE.finditer(text))
    if not matches:
        return text.strip(), []
    compressible = text[: matches[0].start()].strip()
    preserved: list[str] = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        preserved.append(text[m.start() : end].strip())
    return compressible, preserved


def merge_compressed_with_preserved(compressed_body: str, preserved: list[str]) -> str:
    parts: list[str] = []
    if compressed_body and compressed_body.strip():
        parts.append(compressed_body.strip())
    parts.extend(p.strip() for p in preserved if p and p.strip())
    return "\n".join(parts)


def build_coding_must_keep(text: str, extra: set[str] | None = None) -> set[str]:
    """Phrases and globs that must survive compression when structured split is unavailable."""
    terms: set[str] = set(extra or ())
    _, preserved = partition_coding_text(text)
    for block in preserved:
        terms.add(block)
        for glob in re.findall(r"[\w./-]+\*\.\w+", block):
            terms.add(glob)
        for phrase in (
            "research_only",
            "active report mutation",
            "pytest smoke",
            "py -m pytest -q",
        ):
            if phrase.lower() in block.lower():
                terms.add(phrase)
    return terms


def compressible_has_structured_blocks(text: str) -> bool:
    return bool(_MARKER_RE.search(text))
