#!/usr/bin/env python3
"""Build inverted lexical index for Logos Studio semantic router (Phase B tier-0).

Reproduce:
  py scripts/build_logos_studio_semantic_router_lexical_index_v1.py
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_PRESETS = ROOT / "docs/final/artifacts/showroom_meaning_topology_qa_presets_v1_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_studio_semantic_router_lexical_index_v1_latest.json"


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _tokens(text: str) -> list[str]:
    return [t for t in _normalize(text).split(" ") if len(t) >= 2]


def build_index(presets_doc: dict[str, Any]) -> dict[str, Any]:
    inverted: dict[str, set[str]] = {}
    preset_keywords: dict[str, list[str]] = {}
    for preset in presets_doc.get("presets") or []:
        pid = str(preset.get("id") or "")
        if not pid:
            continue
        kws: list[str] = []
        for raw in preset.get("keywords") or []:
            k = _normalize(str(raw))
            if len(k) >= 2:
                kws.append(k)
        prompt = _normalize(str(preset.get("prompt_ko") or ""))
        kws.extend(_tokens(prompt))
        kws = list(dict.fromkeys(kws))
        preset_keywords[pid] = kws
        for kw in kws:
            inverted.setdefault(kw, set()).add(pid)
    entries = [
        {"token": tok, "preset_ids": sorted(pids)}
        for tok, pids in sorted(inverted.items(), key=lambda x: x[0])
    ]
    return {
        "schema": "logos_studio_semantic_router_lexical_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "research_only": True,
        "hypothesis_tier": "B",
        "send_gate": "HOLD",
        "tier": "lexical_tier0",
        "embedding_ready": False,
        "preset_count": len(preset_keywords),
        "token_count": len(entries),
        "preset_keywords": preset_keywords,
        "inverted_index": entries,
        "reproduce": "py scripts/build_logos_studio_semantic_router_lexical_index_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--presets", type=Path, default=DEFAULT_PRESETS)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    doc = json.loads(args.presets.read_text(encoding="utf-8-sig"))
    index = build_index(doc)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "token_count": index["token_count"], "out": str(args.out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
