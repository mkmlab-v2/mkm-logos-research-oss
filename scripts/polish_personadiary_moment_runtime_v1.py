#!/usr/bin/env python3
"""Runtime PersonaDiary moment polish — Azure direct [HYPO]. Ollama generate skipped on live path.

Enable API chain: MKM_PERSONADIARY_MOMENT_RUNTIME_POLISH=auto (default) | 1 | 0

stdin JSON:
  {"summary_ko":"...", "intent":"meal", "query":"..."}

stdout JSON:
  {"summary_ko_polished": "..."|null, "polish_meta": {...}}
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.polish_personadiary_moment_copy_v1 import (  # noqa: E402
    polish_summary_with_fallback,
)


def main(argv: list[str] | None = None) -> int:
    raw = sys.stdin.read()
    if not raw.strip():
        print(json.dumps({"error": "empty_stdin"}, ensure_ascii=False))
        return 1
    try:
        body = json.loads(raw)
    except json.JSONDecodeError:
        print(json.dumps({"error": "invalid_json"}, ensure_ascii=False))
        return 1

    summary = str(body.get("summary_ko") or "")
    intent = str(body.get("intent") or "reflect")
    query = str(body.get("query") or "")
    polished, meta = polish_summary_with_fallback(
        summary,
        intent=intent,
        query=query,
        mode="runtime",
    )
    out: dict[str, Any] = {
        "summary_ko_polished": polished,
        "polish_meta": meta,
    }
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
