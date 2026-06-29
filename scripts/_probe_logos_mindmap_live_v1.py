#!/usr/bin/env python3
"""Probe live studio JS bundles for mindmap deployment markers."""

from __future__ import annotations

import json
import re
import urllib.request

BASE = "https://logos.jema-ai.com"
STUDIO = f"{BASE}/logos-research/studio?q=job_job_suffering_reason&demo=1"


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "mkm-mindmap-probe/1"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def main() -> int:
    html = fetch(STUDIO)
    chunks = []
    for m in re.finditer(r"/_next/static/chunks/[^\"']+\.js", html):
        p = m.group(0)
        if p not in chunks:
            chunks.append(p)

    needles = ("data-logos-path-mindmap", "경로 마인드맵", "고급 감사", "lr-studio-mindmap")
    hits: dict[str, list[str]] = {n: [] for n in needles}

    for rel in chunks[:20]:
        try:
            body = fetch(BASE + rel)
        except Exception:
            continue
        name = rel.rsplit("/", 1)[-1]
        for n in needles:
            if n in body:
                hits[n].append(name)

    out = {
        "schema": "logos_mindmap_live_probe_v1",
        "studio_url": STUDIO,
        "chunk_count": len(chunks),
        "hits": hits,
        "deployed": any(hits["data-logos-path-mindmap"]) and any(hits["경로 마인드맵"]),
    }
    print(json.dumps(out, ensure_ascii=False))
    return 0 if out["deployed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
