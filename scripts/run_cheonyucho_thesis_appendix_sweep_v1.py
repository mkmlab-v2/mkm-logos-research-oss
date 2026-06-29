#!/usr/bin/env python3
"""RISS thesis + KCI journal sweep for 천유초(闡幽抄) appendix / full-text mentions."""

from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs/research/raw/CHEONYUCHO_APPENDIX_BIBLIO_SWEEP_v1.json"
BIBLIO = ROOT / "docs/research/raw/CHEONYUCHO_JEMA_BIBLIO_SWEEP_v1.json"

RISS_QUERIES = [
    ("riss_thesis_cheonyucho", "천유초 이제마", "bebc5a5f5c5e5b5c"),
    ("riss_thesis_hanja", "闡幽抄", "bebc5a5f5c5e5b5c"),
    ("riss_thesis_dongmu_yugo", "동무유고 이제마", "bebc5a5f5c5e5b5c"),
    ("riss_thesis_sasang_chobon", "동의수세보원 사상초본권", "bebc5a5f5c5e5b5c"),
    ("riss_book_park1985", "동무격치고 박석언 1985", "d7345961987b50bf"),
    ("riss_article_appendix", "천유초 부록", "e5dde62c988935b3"),
]

KCI_KNOWN_ARTI_IDS = [
    ("ART001014143", "김남일 2006 한의사회지"),
    ("ART001306406", "판본·동무유고 계통 연구"),
    ("ART002804100", "이제마 성정론 1998"),
]

RISS_KNOWN_CONTROL_NOS = [
    ("ee076abcbb30b5b8ffe0bdc3ef48d419", "d7345961987b50bf", "사상체질과 임상편람 1-2"),
    ("8774e49918c01006ffe0bdc3ef48d419", "d7345961987b50bf", "사상체질과 임상편람 vol.2"),
]

ENCY_PARK1985 = "https://encykorea.aks.ac.kr/Article/E0066180"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fetch(url: str, timeout: int = 35) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (MKM cheonyucho sweep)"})
    return urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "replace")


def riss_search(query: str, mat_type: str, limit: int = 8) -> dict:
    params = {
        "query": query,
        "searchGubun": "true",
        "detailYn": "false",
        "p_mat_type": mat_type,
    }
    url = "https://www.riss.kr/search/Search.do?" + urllib.parse.urlencode(params)
    try:
        html = _fetch(url)
    except OSError as exc:
        return {"query": query, "mat_type": mat_type, "url": url, "error": str(exc), "hits": []}

    hits: list[dict] = []
    for m in re.finditer(
        r'DetailView\.do\?[^"\']*control_no=([a-f0-9]+)[^"\']*["\'][^>]*>([^<]{4,200})<',
        html,
    ):
        title = re.sub(r"\s+", " ", m.group(2)).strip()
        if title in ("국내학술논문", "학위논문", "단행본", "기타"):
            continue
        hits.append(
            {
                "control_no": m.group(1),
                "title_guess": title,
                "detail_url": (
                    f"https://www.riss.kr/search/detail/DetailView.do?"
                    f"p_mat_type={mat_type}&control_no={m.group(1)}"
                ),
            }
        )
        if len(hits) >= limit:
            break

    return {"query": query, "mat_type": mat_type, "url": url, "hit_count": len(hits), "hits": hits}


def riss_detail_snippet(control_no: str, mat_type: str) -> dict:
    url = (
        f"https://www.riss.kr/search/detail/DetailView.do?"
        f"p_mat_type={mat_type}&control_no={control_no}"
    )
    try:
        html = _fetch(url)
    except OSError as exc:
        return {"url": url, "error": str(exc)}

    meta: dict[str, str] = {}
    for m in re.finditer(r'<meta\s+name="([^"]+)"\s+content="([^"]*)"', html):
        meta[m.group(1)] = m.group(2).strip()

    toc_block = ""
    for pat in (
        r"목차</[^>]+>.*?<td[^>]*>(.*?)</td>",
        r"abstract[^>]*>(.*?)</",
        r"초록</[^>]+>.*?<td[^>]*>(.*?)</td>",
    ):
        m = re.search(pat, html, re.S | re.I)
        if m:
            toc_block = re.sub(r"<[^>]+>", " ", m.group(1))
            toc_block = re.sub(r"\s+", " ", toc_block).strip()[:800]
            break

    flags = {
        "has_cheonyucho_ko": "천유초" in html,
        "has_cheonyucho_hanja": "闡幽" in html,
        "has_yugochao": "遺稿" in html,
        "has_geukchigo": "格致" in html or "격치고" in html,
        "has_sasang_chobon": "사상초본" in html or "四象草本" in html,
        "has_appendix_keyword": "부록" in html or "appendix" in html.lower(),
    }
    return {
        "url": url,
        "meta_title": meta.get("title") or meta.get("DC.title"),
        "meta_description": (meta.get("description") or meta.get("DC.description") or "")[:500],
        "toc_snippet": toc_block,
        "flags": flags,
    }


def extract_riss_cheonyu_toc_lines(html: str) -> list[str]:
    lines: list[str] = []
    for m in re.finditer(r".{0,40}闡幽.{0,80}", html):
        line = re.sub(r"<[^>]+>", " ", m.group(0))
        line = re.sub(r"\s+", " ", line).strip()
        if line and line not in lines:
            lines.append(line)
    return lines[:10]


def kci_known_arti_block() -> dict:
    hits: list[dict] = []
    for arti_id, label in KCI_KNOWN_ARTI_IDS:
        detail = kci_detail_flags(arti_id)
        flags = detail.get("flags") or {}
        hits.append(
            {
                "arti_id": arti_id,
                "label": label,
                "detail": detail,
                "classification": classify_appendix_candidate(flags),
            }
        )
    return {"source": "known_arti_ids", "hit_count": len(hits), "hits": hits}


def riss_known_records() -> dict:
    records: list[dict] = []
    for control_no, mat_type, label in RISS_KNOWN_CONTROL_NOS:
        detail = riss_detail_snippet(control_no, mat_type)
        html = ""
        try:
            html = _fetch(detail.get("url", ""))
        except OSError:
            pass
        cheonyu_lines = extract_riss_cheonyu_toc_lines(html) if html else []
        records.append(
            {
                "control_no": control_no,
                "mat_type": mat_type,
                "label": label,
                "detail": detail,
                "cheonyu_toc_lines": cheonyu_lines,
                "toc_hanja_grass_vs_chao": (
                    "闡幽草" if any("闡幽草" in x for x in cheonyu_lines) else (
                        "闡幽抄" if any("闡幽抄" in x for x in cheonyu_lines) else "not_in_toc_html"
                    )
                ),
            }
        )
    return {"records": records}


def encykorea_park1985_probe() -> dict:
    try:
        html = _fetch(ENCY_PARK1985)
    except OSError as exc:
        return {"url": ENCY_PARK1985, "error": str(exc)}
    return {
        "url": ENCY_PARK1985,
        "title": "동무격치고 (박석언 역주 1985)",
        "flags": {
            "has_cheonyucho_ko": "천유초" in html,
            "has_cheonyucho_hanja": "闡幽" in html,
            "has_yugochao": "遺稿抄" in html or "유고초" in html,
            "has_geukchigo": "格致藁" in html,
        },
        "verdict": "1985 edition = 격치고 + appendix 유고초; 천유초 not in encykorea article body",
    }


def kci_search_stub(query: str) -> dict:
    return {
        "query": query,
        "note": "KCI HTML search endpoint blocked/404 from automation UA; use known_arti_ids block",
        "hits": [],
    }


def kci_detail_flags(arti_id: str) -> dict:
    url = (
        "https://www.kci.go.kr/kciportal/ci/sereArticleSearch/ciSereArtiView.kci?"
        f"sereArticleSearchBean.artiId={arti_id}"
    )
    try:
        html = _fetch(url)
    except OSError as exc:
        return {"arti_id": arti_id, "url": url, "error": str(exc)}

    title_m = re.search(r"<title>([^<]+)</title>", html, re.I)
    abstract = ""
    for pat in (r"초록</[^>]+>.*?<td[^>]*>(.*?)</td>", r"abstract[^>]*>(.*?)</"):
        m = re.search(pat, html, re.S | re.I)
        if m:
            abstract = re.sub(r"<[^>]+>", " ", m.group(1))
            abstract = re.sub(r"\s+", " ", abstract).strip()[:600]
            break

    return {
        "arti_id": arti_id,
        "url": url,
        "page_title": title_m.group(1).strip() if title_m else None,
        "abstract_snippet": abstract,
        "flags": {
            "has_cheonyucho_ko": "천유초" in html,
            "has_cheonyucho_hanja": "闡幽" in html,
            "has_yugochao": "遺稿" in html,
            "has_geukchigo": "格致" in html or "격치고" in html,
            "has_sasang_chobon": "사상초본" in html or "四象草本" in html,
            "has_appendix_keyword": "부록" in html,
        },
    }
    url = (
        "https://www.kci.go.kr/kciportal/ci/sereArticleSearch/ciSereArtiView.kci?"
        f"sereArticleSearchBean.artiId={arti_id}"
    )
    try:
        html = _fetch(url)
    except OSError as exc:
        return {"arti_id": arti_id, "url": url, "error": str(exc)}

    title_m = re.search(r"<title>([^<]+)</title>", html, re.I)
    abstract = ""
    for pat in (r"초록</[^>]+>.*?<td[^>]*>(.*?)</td>", r"abstract[^>]*>(.*?)</"):
        m = re.search(pat, html, re.S | re.I)
        if m:
            abstract = re.sub(r"<[^>]+>", " ", m.group(1))
            abstract = re.sub(r"\s+", " ", abstract).strip()[:600]
            break

    return {
        "arti_id": arti_id,
        "url": url,
        "page_title": title_m.group(1).strip() if title_m else None,
        "abstract_snippet": abstract,
        "flags": {
            "has_cheonyucho_ko": "천유초" in html,
            "has_cheonyucho_hanja": "闡幽" in html,
            "has_yugochao": "遺稿" in html,
            "has_geukchigo": "格致" in html or "격치고" in html,
            "has_sasang_chobon": "사상초본" in html or "四象草本" in html,
            "has_appendix_keyword": "부록" in html,
        },
    }


def classify_appendix_candidate(flags: dict) -> str:
    if flags.get("has_cheonyucho_hanja") or flags.get("has_cheonyucho_ko"):
        if flags.get("has_appendix_keyword"):
            return "cheonyucho_plus_appendix_keyword"
        return "cheonyucho_mention_only"
    if flags.get("has_sasang_chobon") or flags.get("has_geukchigo") or flags.get("has_yugochao"):
        return "related_manuscript_not_cheonyucho"
    return "no_cheonyucho_signal"


def main() -> int:
    doc: dict[str, object] = {
        "schema": "cheonyucho_appendix_biblio_sweep_v1",
        "generated_at_utc": _utc(),
        "ssot_hanja": "闡幽抄",
        "send_gate": "HOLD",
        "canon_status": "not_acquired",
        "verdict": {
            "thesis_fulltext_appendix_found": False,
            "park1985_includes_cheonyucho_toc": "unverified_until_physical",
            "mediclassics_cheonyucho_title": False,
            "note": "Automated HTML sweep only; PDF grep required for appendix full-text claims.",
        },
        "riss": {},
        "riss_known": {},
        "kci": {},
        "kci_known": {},
        "encykorea": {},
        "candidates": [],
    }

    for key, query, mat_type in RISS_QUERIES:
        block = riss_search(query, mat_type)
        enriched: list[dict] = []
        for hit in block.get("hits", [])[:3]:
            cno = hit.get("control_no")
            if cno:
                detail = riss_detail_snippet(cno, mat_type)
                hit = {**hit, "detail": detail}
                flags = detail.get("flags") or {}
                cls = classify_appendix_candidate(flags)
                hit["classification"] = cls
                if cls.startswith("cheonyucho"):
                    doc["candidates"].append(  # type: ignore[union-attr]
                        {"source": "riss", "key": key, **hit}
                    )
            enriched.append(hit)
        block["hits"] = enriched
        doc["riss"][key] = block  # type: ignore[index]

    doc["riss_known"] = riss_known_records()
    for rec in doc["riss_known"].get("records", []):  # type: ignore[union-attr]
        for line in rec.get("cheonyu_toc_lines", []):
            if "闡幽" in line:
                doc["candidates"].append(  # type: ignore[union-attr]
                    {
                        "source": "riss_known",
                        "label": rec.get("label"),
                        "toc_line": line,
                        "classification": "cheonyucho_toc_entry_not_fulltext",
                    }
                )

    doc["kci_known"] = kci_known_arti_block()
    for hit in doc["kci_known"].get("hits", []):  # type: ignore[union-attr]
        if str(hit.get("classification", "")).startswith("cheonyucho"):
            doc["candidates"].append({"source": "kci_known", **hit})  # type: ignore[arg-type]

    doc["encykorea"] = encykorea_park1985_probe()
    if not doc["encykorea"].get("flags", {}).get("has_cheonyucho_hanja"):  # type: ignore[union-attr]
        doc["verdict"]["park1985_includes_cheonyucho_toc"] = "unlikely_per_encykorea_E0066180"  # type: ignore[index]

    # legacy kci query stubs (portal search 404 from bot UA)
    for i, query in enumerate(["천유초", "闡幽抄", "동무유고 이제마", "동의수세보원 사상초본권"]):
        doc["kci"][f"kci_q_{i+1}"] = kci_search_stub(query)  # type: ignore[index]

    # mediclassics quick probe
    try:
        mc_html = _fetch("https://www.mediclassics.kr/search?query=%EC%B2%9C%EC%9C%A0%EC%B4%88")
        doc["mediclassics"] = {
            "url": "https://www.mediclassics.kr/search?query=천유초",
            "has_cheonyucho_ko": "천유초" in mc_html,
            "has_cheonyucho_hanja": "闡幽" in mc_html,
            "homonym_warning": "천문유초" in mc_html,
        }
        doc["verdict"]["mediclassics_cheonyucho_title"] = bool(  # type: ignore[index]
            "闡幽" in mc_html and "이제마" in mc_html
        )
    except OSError as exc:
        doc["mediclassics"] = {"error": str(exc)}

    doc["verdict"]["thesis_fulltext_appendix_found"] = any(  # type: ignore[index]
        c.get("classification") == "cheonyucho_plus_appendix_keyword" for c in doc.get("candidates", [])
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if BIBLIO.is_file():
        bib = json.loads(BIBLIO.read_text(encoding="utf-8"))
        bib["appendix_biblio_sweep"] = str(OUT.relative_to(ROOT)).replace("\\", "/")
        bib["appendix_sweep_at_utc"] = doc["generated_at_utc"]
        bib["thesis_appendix_found"] = doc["verdict"]["thesis_fulltext_appendix_found"]  # type: ignore[index]
        BIBLIO.write_text(json.dumps(bib, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # patch acquisition probe P1-04 if present
    probe_path = ROOT / "reports/constitution/btrack_pilot/cheonyucho_acquisition_probe_v1.json"
    if probe_path.is_file():
        probe = json.loads(probe_path.read_text(encoding="utf-8"))
        for item in probe.get("checklist", []):
            if item.get("id") == "P1-07":
                item["status"] = "thesis_appendix_sweep_run"
                item["artifact"] = str(OUT.relative_to(ROOT)).replace("\\", "/")
                item["candidate_count"] = len(doc.get("candidates", []))
        probe["updated_at_utc"] = _utc()
        probe_path.write_text(json.dumps(probe, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "out": str(OUT),
                "candidates": len(doc.get("candidates", [])),
                "thesis_appendix_found": doc["verdict"]["thesis_fulltext_appendix_found"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
