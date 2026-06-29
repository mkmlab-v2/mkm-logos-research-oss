#!/usr/bin/env python3
"""Harness step 2: local intent router (heuristic · tier_0) for B-track ingest gates.

Routes: local_math | exa_scout | bigset_ingest | azure_bigset | hold_research

Reproducible:
  py scripts/mkm_intent_router_local_v1.py --query "창세기 6장 게마트리아"
"""

from __future__ import annotations

import argparse
import json
import re
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.bigset_free_tier_profile_v1 import azure_credentials_present, load_dotenv_quiet  # noqa: E402

OUT_ART = ROOT / "docs/final/artifacts/mkm_intent_router_local_v1_latest.json"

MATH_PAT = re.compile(
    r"게마트리아|gematria|수치\s*계산|checksum|mod\s*\d+|소인수|연산",
    re.IGNORECASE,
)
WEB_PAT = re.compile(
    r"논문|url|검색|exa|tinyfish|웹|corpus|tier-?0|bigset|인용|citation|cross.?ref",
    re.IGNORECASE,
)
THEOLOGY_PAT = re.compile(
    r"창세기|성경|benei|haelohim|sons of god|logos|신학|1\s*enoch|lxx|dss",
    re.IGNORECASE,
)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def route(query: str) -> dict[str, object]:
    q = (query or "").strip()
    load_dotenv_quiet()
    if not q:
        return {"route": "hold_research", "reason": "empty_query", "gates": []}
    if MATH_PAT.search(q) and not WEB_PAT.search(q):
        return {
            "route": "local_math",
            "reason": "mathematical_or_gematria_without_web_scout",
            "gates": ["skip_exa", "skip_bigset", "use_mkm_math_engine"],
        }
    if THEOLOGY_PAT.search(q) or WEB_PAT.search(q):
        if azure_credentials_present() and (os.environ.get("MKM_LLM_PRIORITY") or "").strip() == "azure_first":
            return {
                "route": "azure_bigset",
                "reason": "web_or_theology_corpus_azure_first",
                "gates": ["read_ssot", "bigset_azure_profile", "citation_lock"],
            }
        return {
            "route": "bigset_ingest",
            "reason": "web_or_theology_corpus",
            "gates": ["read_ssot", "bigset_profile", "citation_lock"],
        }
    if WEB_PAT.search(q):
        return {
            "route": "exa_scout",
            "reason": "web_scout_only",
            "gates": ["exa_mcp_or_tinyfish", "no_track_a_merge"],
        }
    return {"route": "hold_research", "reason": "unclassified_b_track", "gates": ["send_gate_hold"]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", required=True)
    ap.add_argument("--artifact", type=Path, default=OUT_ART)
    args = ap.parse_args()

    result = route(args.query)
    doc = {
        "schema": "mkm_intent_router_local_v1",
        "generated_at_utc": _now(),
        "research_only": True,
        "send_gate": "HOLD",
        "ok": True,
        "query": args.query,
        **result,
        "reproduce": "py scripts/mkm_intent_router_local_v1.py --query \"...\"",
    }
    args.artifact.parent.mkdir(parents=True, exist_ok=True)
    args.artifact.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "route": result.get("route"), "artifact": str(args.artifact.relative_to(ROOT))}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
