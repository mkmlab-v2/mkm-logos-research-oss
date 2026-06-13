#!/usr/bin/env python3
"""Lexicon lookup smoke — bridge join only; no chat injection.

  py scripts/check_lexicon_lookup_smoke_v1.py

Output: reports/lexicon_lookup_smoke_v1_latest.json
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/lexicon_lookup_smoke_v1_latest.json"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.core.master_codebook_lexicon_v1_bridge import (  # noqa: E402
    lexicon_hits_for_text,
    resolve_latest_codebook_path,
)

SAMPLE_TEXT = "레짐 압축 must_keep normalized_form atom_id 교차 검증"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    path = resolve_latest_codebook_path()
    payload: dict[str, Any] = {
        "schema": "lexicon_lookup_smoke_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "bridge": "scripts/core/master_codebook_lexicon_v1_bridge.py",
        "chat_injection": False,
        "lexicon_path": path.relative_to(ROOT).as_posix() if path else None,
        "ok": False,
        "reproduce": "py scripts/check_lexicon_lookup_smoke_v1.py",
    }
    if path is None:
        payload["error"] = "lexicon_path_not_found"
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps({"ok": False, "error": payload["error"]}, ensure_ascii=False))
        return 1

    hits, meta = lexicon_hits_for_text(SAMPLE_TEXT, path, include_cjk_bigrams=True)
    payload["sample_text"] = SAMPLE_TEXT
    payload["hit_count"] = meta.get("hit_count", len(hits))
    payload["sample_hits"] = sorted(hits)[:5]
    payload["meta"] = meta
    payload["ok"] = payload["hit_count"] > 0

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok": payload["ok"], "hit_count": payload["hit_count"], "out": str(OUT)}, ensure_ascii=False))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
