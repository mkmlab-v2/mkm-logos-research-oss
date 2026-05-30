#!/usr/bin/env python3
"""One-shot live + contract auto-verify for Oracle Sphere showroom (q01/q04–q08)."""
from __future__ import annotations

import hashlib
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

UA = {"User-Agent": "MKM-auto-verify/1.0"}
ORIGIN = "https://mkmlife.com"
FIXTURE = ROOT / "docs/final/fixtures/magic_orb_question_insight_queries_v1.json"

GOLD_QUERY_IDS = ("q01", "q02", "q03", "q04", "q05", "q06", "q07", "q08")
Q01 = "위기 가운데 언약의 안정과 신실"


def _query_hash16(query: str) -> str:
    norm = " ".join(query.strip().split())[:800]
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()[:16]


def _load_gold_queries() -> dict[str, str]:
    doc = json.loads(FIXTURE.read_text(encoding="utf-8-sig"))
    out: dict[str, str] = {}
    for item in doc.get("items") or []:
        if not isinstance(item, dict):
            continue
        qid = str(item.get("id") or "")
        qko = str(item.get("query_ko") or "")
        if qid in GOLD_QUERY_IDS and qko:
            out[qid] = qko
    return out


def get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=45) as resp:
        return json.loads(resp.read())


def _check_gold_query(checks: list[tuple[str, bool, str]], qid: str, query: str) -> None:
    qhash = _query_hash16(query)
    api = get_json(f"{ORIGIN}/api/v1/magic-orb/insight?query={urllib.parse.quote(query)}")
    payload = api.get("payload") or {}
    gb = payload.get("graph_bloom") or {}
    n_api = len(gb.get("nodes") or [])
    checks.append((f"{qid}_api_nodes_64", n_api == 64, f"nodes={n_api} source={api.get('source')}"))
    checks.append((f"{qid}_query_id", payload.get("query_id") == qid, str(payload.get("query_id"))))

    static = get_json(f"{ORIGIN}/data/magic_orb_insight_by_query/{qhash}.json")
    n_static = len((static.get("graph_bloom") or {}).get("nodes") or [])
    checks.append((f"{qid}_static_nodes_64", n_static == 64, f"hash={qhash} nodes={n_static}"))

    rag = static.get("rag_evidence") or []
    raw = sum(1 for r in rag if "steps=[" in (r.get("snippet") or ""))
    checks.append((f"{qid}_no_raw_steps_snippet", raw == 0, f"raw_steps_rows={raw}"))
    ko = sum(1 for r in rag if re.search(r"[\uac00-\ud7a3]", r.get("snippet") or ""))
    checks.append((f"{qid}_ko_snippets", ko >= 3, f"ko_snippet_rows={ko}/{len(rag)}"))


def main() -> int:
    checks: list[tuple[str, bool, str]] = []
    gold = _load_gold_queries()

    for qid in GOLD_QUERY_IDS:
        query = gold.get(qid)
        if not query:
            checks.append((f"{qid}_fixture", False, "missing query_ko in fixture"))
            continue
        _check_gold_query(checks, qid, query)

    # q04 HUD bloom cap (representative dense gold)
    q04 = gold.get("q04")
    if q04:
        q04_api = get_json(f"{ORIGIN}/api/v1/magic-orb/insight?query={urllib.parse.quote(q04)}")
        hud = (q04_api.get("payload") or {}).get("search_hud_v1") or {}
        tq = hud.get("this_query") or {}
        checks.append(("q04_hud_bloom_64", tq.get("bloom_nodes") == 64, json.dumps(tq, ensure_ascii=False)))
        me = (hud.get("corpus") or {}).get("meaning_graph_edge_count")
        checks.append(("hud_meaning_edges_present", isinstance(me, int) and me > 0, f"meaning_graph_edge_count={me}"))

    html = urllib.request.urlopen(
        urllib.request.Request(f"{ORIGIN}/oracle-sphere", headers=UA), timeout=45
    ).read().decode("utf-8", "ignore")
    has_oracle_page_chunk = bool(re.search(r"oracle-sphere/page-[a-f0-9]+\.js", html))
    checks.append(("deploy_oracle_page_chunk", has_oracle_page_chunk, "oracle-sphere app chunk present"))
    checks.append(("page_http_200", "magic-orb-page" in html, "oracle-sphere shell markers"))

    from tests.test_magic_orb_graph_bloom_label_helpers_v1 import (
        humanize_bloom_verse_ref,
        should_skip_bloom_canvas_label,
    )

    checks.append(
        (
            "label_skip_theme_dup",
            should_skip_bloom_canvas_label("위기 가운데 언약의 안정", Q01),
            "pill overlap guard",
        )
    )
    checks.append(
        (
            "label_humanize_ps",
            humanize_bloom_verse_ref("Ps.89.28") == "시편 89:28",
            str(humanize_bloom_verse_ref("Ps.89.28")),
        )
    )

    out = {
        "schema": "oracle_sphere_showroom_auto_verify_v1",
        "origin": ORIGIN,
        "overall_ok": all(c[1] for c in checks),
        "checks": [{"id": c[0], "ok": c[1], "detail": c[2]} for c in checks],
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out["overall_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
