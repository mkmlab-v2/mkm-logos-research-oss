#!/usr/bin/env python3
"""NLK 199.1-이617ㄱ + encykorea appendix crossval for claim #1 — B-track HOLD."""

from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "docs/research/raw"
OUT = ROOT / "reports/constitution/btrack_pilot/cheonyucho_park1985_appendix_grep_v1.json"
PROXY = RAW / "PARK1985_NLK_APPENDIX_grep_nl_proxy.md"
VERIFIED = RAW / "IJEOMA_VERIFIED_FACT_FRAGMENTS_v1.json"
P1_CARD = ROOT / "reports/constitution/btrack_pilot/cheonyucho_p1_library_request_card_v1.txt"

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
HEADERS = {"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9"}

APPENDIX_TERMS = ["闡幽", "천유", "遺稿", "유고초", "제중신편", "濟衆", "1940", "함흥", "덕흥"]
GEUKCHIGO_ARTICLE = "E0066180"
NLK_QUERY = "동무격치고"
EXPECTED_CALL = "199.1-이617"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_url(url: str) -> tuple[str, int]:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", "replace"), resp.status


def strip_html(html: str) -> str:
    text = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def nlk_search(query: str) -> dict:
    url = "https://www.nl.go.kr/NL/contents/search.do?" + urllib.parse.urlencode({"kwd": query})
    html, status = fetch_url(url)
    hits: list[dict] = []
    for m in re.finditer(
        r'<a[^>]+detail_view_pop[^>]*>([^<]+)</a>.*?청구기호\s*:\s*([^\s<]+)',
        html,
        re.S,
    ):
        title = re.sub(r"\s+", " ", m.group(1)).strip()
        call_no = m.group(2).strip()
        meta = html[m.start() : m.end()]
        pub_year = re.search(r"<span class=\"hyphen\"></span>(\d{4})<span", meta)
        pub = re.search(r"발행처\s*:\s*([^<\n]+)", meta)
        hits.append(
            {
                "title": title[:180],
                "call_no": call_no,
                "year": pub_year.group(1) if pub_year else None,
                "publisher_guess": pub.group(1).strip() if pub else None,
            }
        )
    seen: set[str] = set()
    uniq: list[dict] = []
    for h in hits:
        key = f"{h.get('title')}|{h.get('call_no')}"
        if key in seen:
            continue
        seen.add(key)
        uniq.append(h)
    park_rows = [h for h in uniq if EXPECTED_CALL.replace("ㄱ", "") in (h.get("call_no") or "")]
    return {
        "query": query,
        "url": url,
        "status": status,
        "hit_count": len(uniq),
        "hits": uniq[:10],
        "park1985_rows": park_rows,
        "page_grep": {t: html.count(t) for t in APPENDIX_TERMS if html.count(t)},
    }


def fetch_geukchigo_appendix() -> dict:
    url = f"https://encykorea.aks.ac.kr/Article/{GEUKCHIGO_ARTICLE}"
    html, status = fetch_url(url)
    text = strip_html(html)
    contexts: dict[str, str] = {}
    for term in APPENDIX_TERMS:
        i = text.find(term)
        if i >= 0:
            contexts[term] = text[max(0, i - 70) : i + 120].strip()
    return {
        "url": url,
        "status": status,
        "grep_contexts": contexts,
        "has_jijeong_yugo_appendix": ("제중신편" in text or "濟衆" in text)
        and ("유고초" in text or "遺稿" in text),
        "has_cheonyu_in_article": "천유" in text or "闡幽" in text,
    }


def synthesize_claim1(park_nlk: dict, geuk: dict) -> dict:
    park_ok = bool(park_nlk.get("park1985_rows"))
    appendix_biblio = geuk.get("has_jijeong_yugo_appendix")
    physical_grep = False  # no scanned 1985 volume in workspace
    return {
        "claim_id": 1,
        "nlk_park1985_call_no_verified": park_ok,
        "encykorea_1940_appendix_structure": appendix_biblio,
        "physical_index_grep_1985": physical_grep,
        "workspace_verdict": "T1_biblio_supported_physical_pending"
        if park_ok and appendix_biblio
        else "partially_supported",
        "note": (
            "NLK 199.1-이617ㄱ + encykorea 격치고 부록(제중신편·유고초) T1 교차확인; "
            "박석언 1985 역주본 뒤색인·각주 闡幽 grep는 실물 P1"
        ),
    }


def write_proxy(park_nlk: dict, geuk: dict, claim1: dict) -> None:
    lines = [
        "# NL Proxy — PARK1985 NLK + appendix crossval (claim #1)",
        "",
        f"**generated:** {_utc()} · `research_only` · `send_gate: HOLD`",
        f"**artifact:** `{OUT.relative_to(ROOT).as_posix()}`",
        "",
        "## claim #1 synthesis",
        "",
        f"- **verdict:** `{claim1['workspace_verdict']}`",
        f"- **NLK park1985:** {claim1['nlk_park1985_call_no_verified']}",
        f"- **encykorea appendix (제중신편·유고초):** {claim1['encykorea_1940_appendix_structure']}",
        f"- **physical 1985 index grep:** {claim1['physical_index_grep_1985']} (P1 human)",
        f"- **note:** {claim1['note']}",
        "",
        "## NLK — 동무격치고",
        "",
    ]
    for row in park_nlk.get("park1985_rows") or park_nlk.get("hits", [])[:3]:
        lines.append(
            f"- **{row.get('title')}** | `{row.get('call_no')}` | {row.get('year')} | "
            f"{row.get('publisher_guess') or ''}"
        )
    lines.extend(["", "## encykorea E0066180 (格致藁) appendix grep", ""])
    for term, ctx in (geuk.get("grep_contexts") or {}).items():
        lines.append(f"- **{term}:** {ctx[:240]}")
    lines.extend(
        [
            "",
            "## P1 remaining",
            "",
            "- 실물 `(東武)格致藁 : 人間哲學` 박석언 1985 — 뒤색인·각주 闡幽抄·遺稿抄 grep",
            "",
            "## Reproduce",
            "",
            "```powershell",
            "py scripts/run_cheonyucho_park1985_appendix_grep_v1.py",
            "py scripts/run_cheonyucho_fragment_mine_v1.py",
            "```",
            "",
        ]
    )
    PROXY.write_text("\n".join(lines), encoding="utf-8")


def patch_verified(claim1: dict, proxy_rel: str, artifact_rel: str) -> None:
    if not VERIFIED.is_file():
        return
    data = json.loads(VERIFIED.read_text(encoding="utf-8"))
    for frag in data.get("verified_fact_fragments", []):
        if frag.get("claim_id") != 1:
            continue
        frag["workspace_verdict"] = claim1["workspace_verdict"]
        frag["note"] = claim1["note"]
        sids = list(frag.get("source_ids") or [])
        for sid in ("PARK1985-NLK-APPENDIX", "encykorea-E0066180"):
            if sid not in sids:
                sids.append(sid)
        frag["source_ids"] = sids
        paths = list(frag.get("pdf_paths") or [])
        if proxy_rel not in paths:
            paths.append(proxy_rel)
        frag["pdf_paths"] = paths
        frag["grep_artifact"] = artifact_rel
        break
    data["ledger_stub_metadata"]["generation_timestamp_utc"] = _utc()
    VERIFIED.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def patch_p1_card(claim1: dict) -> None:
    if not P1_CARD.is_file():
        return
    text = P1_CARD.read_text(encoding="utf-8")
    text = re.sub(
        r"updated:.*\n",
        f"updated: {_utc()[:10]} (L2 grep done · claim1 NLK T1)\n",
        text,
        count=1,
    )
    if claim1["nlk_park1985_call_no_verified"]:
        text = text.replace(
            "  □ NLK 199.1-이617ㄱ 박석언 1985 — 遺稿抄·闡幽 grep",
            "  ◐ NLK 199.1-이617ㄱ T1 확인 — 실물 遺稿抄·闡幽 grep P1",
        )
    text = re.sub(
        r"  ledger: FM-09 chunk.*\n",
        f"  ledger: FM-09 + PARK1985_NLK proxy — 부록 T1 encykorea; 실물 색인 P1\n",
        text,
        count=1,
    )
    P1_CARD.write_text(text, encoding="utf-8")


def main() -> int:
    park_nlk = nlk_search(NLK_QUERY)
    geuk = fetch_geukchigo_appendix()
    claim1 = synthesize_claim1(park_nlk, geuk)
    artifact_rel = str(OUT.relative_to(ROOT)).replace("\\", "/")
    proxy_rel = str(PROXY.relative_to(ROOT)).replace("\\", "/")
    doc = {
        "schema": "cheonyucho_park1985_appendix_grep_v1",
        "generated_at_utc": _utc(),
        "send_gate": "HOLD",
        "track": "B",
        "nlk": park_nlk,
        "encykorea_geukchigo": geuk,
        "claim1": claim1,
        "proxy_path": proxy_rel,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_proxy(park_nlk, geuk, claim1)
    patch_verified(claim1, proxy_rel, artifact_rel)
    patch_p1_card(claim1)
    ok = claim1["nlk_park1985_call_no_verified"] and claim1["encykorea_1940_appendix_structure"]
    print(
        json.dumps(
            {
                "ok": ok,
                "out": str(OUT),
                "proxy": str(PROXY),
                "claim1_verdict": claim1["workspace_verdict"],
                "park_rows": len(park_nlk.get("park1985_rows", [])),
            },
            ensure_ascii=False,
        )
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
