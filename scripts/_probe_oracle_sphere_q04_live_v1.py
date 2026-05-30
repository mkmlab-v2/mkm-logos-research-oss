#!/usr/bin/env python3
"""One-shot live check: oracle-sphere page + q04 static/API."""
from __future__ import annotations

import json
import urllib.parse
import urllib.request

UA = {"User-Agent": "MKM-probe/1.0"}
Q04 = (
    "심판의 경고 이후에도 언약의 잔류가 남는다는 성경적 논증은, "
    "어떤 구절·경로(chain)로 연결되는가?"
)
URLS = {
    "q04_static": "https://mkmlife.com/data/magic_orb_insight_by_query/482fb24be6f1ec09.json",
    "q04_api": "https://mkmlife.com/api/v1/magic-orb/insight?query=" + urllib.parse.quote(Q04),
    "oracle_page": "https://mkmlife.com/oracle-sphere",
}


def main() -> int:
    out: dict = {}
    for key, url in URLS.items():
        req = urllib.request.Request(url, headers=UA)
        try:
            resp = urllib.request.urlopen(req, timeout=30)
            body = resp.read().decode("utf-8", "replace")
            item: dict = {"status": resp.status, "bytes": len(body)}
            if key.startswith("q04"):
                doc = json.loads(body)
                gb = doc.get("graph_bloom") or {}
                stats = gb.get("stats") or {}
                rag0 = (doc.get("rag_evidence") or [{}])[0].get("snippet", "")[:200]
                item.update(
                    {
                        "query_id": doc.get("query_id"),
                        "nodes": stats.get("node_count"),
                        "edges": stats.get("edge_count"),
                        "rag_count": len(doc.get("rag_evidence") or []),
                        "snippet_head": rag0,
                        "has_bridge": "logos_concept_bridge_gold_q04_judgment_covenant_remnant"
                        in body,
                        "has_raw_steps": ("match_score=" in rag0) or ('"steps":' in rag0),
                    }
                )
            else:
                item["has_magic_orb"] = ("magic-orb-page" in body) or ("마법구슬" in body)
                item["has_disclaimer"] = "NON-MEDICAL" in body
            out[key] = item
        except Exception as exc:  # noqa: BLE001
            out[key] = {"error": str(exc)}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    ok = all("error" not in v for v in out.values())
    if ok and out.get("q04_static", {}).get("nodes") == 64:
        return 0
    return 1 if not ok else 0


if __name__ == "__main__":
    raise SystemExit(main())
