#!/usr/bin/env python3
"""Offline gate: mkm_domain_design_tokens_v1.json schema and hub paths exist."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOKENS = ROOT / "docs/final/artifacts/mkm_domain_design_tokens_v1.json"
REQUIRED_DOMAINS = ("mkmlife.com", "jema-ai.com", "jemaai.cloud", "personadiary.com")


def main() -> int:
    if not TOKENS.is_file():
        print(f"MISSING: {TOKENS}", file=sys.stderr)
        return 1
    doc = json.loads(TOKENS.read_text(encoding="utf-8"))
    if doc.get("schema") != "mkm_domain_design_tokens_v1":
        print("bad schema", file=sys.stderr)
        return 1
    domains = doc.get("domains") or {}
    missing = [d for d in REQUIRED_DOMAINS if d not in domains]
    if missing:
        print(f"missing domains: {missing}", file=sys.stderr)
        return 1
    for key, row in domains.items():
        palette = row.get("palette") or {}
        if not all(k in palette for k in ("bg", "accent", "muted")):
            print(f"bad palette: {key}", file=sys.stderr)
            return 1
        for path_key in ("css_ssot", "html_ssot", "route_ssot"):
            rel = row.get(path_key)
            if not rel:
                continue
            if not (ROOT / rel).is_file():
                print(f"missing path {path_key}={rel} for {key}", file=sys.stderr)
                return 1
    hub = ROOT / doc.get("hub_cta_ssot", "")
    if not hub.is_file():
        print(f"missing hub_cta_ssot: {hub}", file=sys.stderr)
        return 1
    print(json.dumps({"overall_ok": True, "domains": list(domains.keys())}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
