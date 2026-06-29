#!/usr/bin/env python3
"""JSG + NLK catalog probe for cheonyucho P1."""

from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports/constitution/btrack_pilot/cheonyucho_external_catalog_probe_v1.json"

JSG_TERMS = ["格致藁", "闡幽抄", "東武遺稿", "東醫壽世保元"]
NLK_QUERIES = [
    ("sasang_isbn", "9788992971690"),
    ("sasang_title", "사상체질과 임상편람"),
    ("park1985", "동무격치고"),
    ("cheonyucho", "천유초"),
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def jsg_search(term: str, page_unit: int = 20) -> dict:
    q = urllib.parse.quote(term)
    url = f"https://jsg.aks.ac.kr/api/search?qw=dataName&q={q}&startIndex=0&pageUnit={page_unit}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    raw = urllib.request.urlopen(req, timeout=30).read()
    data = json.loads(raw.decode("utf-8", "replace"))
    items = data.get("list") or data.get("items") or []
    hits = []
    for it in items[:page_unit]:
        if not isinstance(it, dict):
            continue
        hits.append(
            {
                "dataName": it.get("dataName") or it.get("title"),
                "dataId": it.get("dataId") or it.get("id"),
                "callNum": it.get("callNum") or it.get("callNo"),
                "author": it.get("author"),
                "url": (
                    f"https://jsg.aks.ac.kr/dir/view?dataId={it.get('dataId')}"
                    if it.get("dataId")
                    else None
                ),
            }
        )
    return {
        "term": term,
        "total": data.get("totalCount") or data.get("total") or len(hits),
        "hits": hits,
    }


def nlk_search(query: str) -> dict:
    url = "https://www.nl.go.kr/NL/contents/search.do?" + urllib.parse.urlencode({"kwd": query})
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
    hits: list[dict] = []
    for m in re.finditer(
        r'<a[^>]+detail_view_pop[^>]*>([^<]+)</a>.*?'
        r'청구기호\s*:\s*([^\s<]+)',
        html,
        re.S,
    ):
        title = re.sub(r"\s+", " ", m.group(1)).strip()
        call_no = m.group(2).strip()
        meta = html[m.start() : m.end()]
        pub_year = re.search(r"<span class=\"hyphen\"></span>(\d{4})<span", meta)
        hits.append(
            {
                "title": title[:160],
                "call_no": call_no,
                "year": pub_year.group(1) if pub_year else None,
            }
        )
    if not hits:
        for m in re.finditer(r"책제목\s*:\s*([^<\n]+).*?청구기호\s*:\s*([^\s<]+)", html, re.S):
            hits.append({"title": m.group(1).strip(), "call_no": m.group(2).strip()})
    seen: set[str] = set()
    uniq: list[dict] = []
    for h in hits:
        key = f"{h.get('title')}|{h.get('call_no')}"
        if key in seen:
            continue
        seen.add(key)
        uniq.append(h)
    return {"query": query, "hit_count": len(uniq), "hits": uniq[:10]}


def main() -> int:
    doc: dict[str, object] = {
        "schema": "cheonyucho_external_catalog_probe_v1",
        "generated_at_utc": _utc(),
        "jsg": {},
        "nlk": {},
    }
    for term in JSG_TERMS:
        try:
            doc["jsg"][term] = jsg_search(term)  # type: ignore[index]
        except Exception as exc:
            doc["jsg"][term] = {"term": term, "error": str(exc)}  # type: ignore[index]

    for key, q in NLK_QUERIES:
        try:
            doc["nlk"][key] = nlk_search(q)  # type: ignore[index]
        except Exception as exc:
            doc["nlk"][key] = {"query": q, "error": str(exc)}  # type: ignore[index]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # patch library card + probe
    card = ROOT / "reports/constitution/btrack_pilot/cheonyucho_p1_library_request_card_v1.txt"
    nlk = doc.get("nlk") or {}
    if card.is_file() and isinstance(nlk, dict):
        text = card.read_text(encoding="utf-8")
        if "[NLK 자동 프로브]" not in text:
            extra = ["", "[NLK 자동 프로브]"]
            for key in ("sasang_isbn", "park1985", "cheonyucho"):
                block = nlk.get(key)
                if isinstance(block, dict):
                    for h in block.get("hits", [])[:2]:
                        extra.append(
                            f"  - {key}: {h.get('title')} | 청구 {h.get('call_no')} | {h.get('year') or ''}"
                        )
            card.write_text(text.rstrip() + "\n" + "\n".join(extra) + "\n", encoding="utf-8")

    probe_path = ROOT / "reports/constitution/btrack_pilot/cheonyucho_acquisition_probe_v1.json"
    if probe_path.is_file():
        probe = json.loads(probe_path.read_text(encoding="utf-8"))
        for item in probe.get("checklist", []):
            if item["id"] == "P1-02":
                item["status"] = "jsg_api_probe_run"
                item["artifact"] = str(OUT.relative_to(ROOT)).replace("\\", "/")
            if item["id"] == "P1-03":
                item["status"] = "nlk_html_probe_run"
                item["external_catalog"] = str(OUT.relative_to(ROOT)).replace("\\", "/")
            if item["id"] == "P1-01":
                park = (nlk.get("park1985") or {}).get("hits", []) if isinstance(nlk, dict) else []
                if park:
                    item["status"] = "nlk_call_no_confirmed"
                    item["nlk_call_no"] = park[0].get("call_no")
                    item["nlk_title"] = park[0].get("title")
                    item["note"] = "NLK 청구기호 확인; 뒤색인 grep는 열람실"
            if item["id"] == "P1-06" and isinstance(nlk, dict):
                sasang = (nlk.get("sasang_isbn") or {}).get("hits", [])
                if sasang:
                    item["nlk_call_no"] = sasang[0].get("call_no")
                    item["nlk_hits"] = sasang[:2]
        probe["updated_at_utc"] = _utc()
        probe_path.write_text(json.dumps(probe, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"ok": True, "out": str(OUT)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
