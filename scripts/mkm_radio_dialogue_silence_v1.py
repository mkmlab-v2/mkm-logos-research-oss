"""Turn-gap silence ms for 3-DJ dialogue render (persona / tags)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def silence_ms_between(prev: Optional[Dict[str, Any]], cur: Dict[str, Any]) -> int:
    if prev is None:
        return 0
    tags = set(cur.get("copy_tags") or [])
    if prev.get("persona") != cur.get("persona"):
        base = 800
        if "SASANG" in tags:
            return max(base, 900)
        return base
    if "SASANG" in tags:
        return 500
    if "DISCLAIMER" in tags:
        return 400
    return 350
