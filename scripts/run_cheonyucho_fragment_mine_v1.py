#!/usr/bin/env python3
"""B-track fragment mine: Tier0 OA harvest + Tier1 Exa discovery → chunk ledger (HOLD)."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "docs/research/raw"
OUT_LEDGER = RAW / "CHEONYUCHO_FRAGMENT_LEDGER_v1.json"
OUT_EXA_META = ROOT / "reports/constitution/btrack_pilot/cheonyucho_fragment_exa_discover_v1.json"
SECONDARY_MANIFEST = RAW / "CHEONYUCHO_SECONDARY_CORPUS_v1.json"
EXA_SEARCH_URL = "https://api.exa.ai/search"

# Priority: 격치고 > 동무유고 > 闡幽抄 (commander order)
TIER0_TARGETS: list[dict] = [
    {
        "id": "FM-07",
        "title": "『格致藁ㆍ儒略』에 관한 考察",
        "authors": "사상체질면역의학회",
        "year": 2005,
        "fetch": "jscim",
        "arti_id": "ART001019799",
        "slug": "GYUKCHIGO_YURYAK_2005",
        "focus": "geukchigo",
    },
    {
        "id": "FM-08",
        "title": "李濟馬의 獨行篇에 對한 考察",
        "authors": "金鍾元·高炳熙",
        "year": 1994,
        "fetch": "jscim",
        "arti_id": "ART002803635",
        "slug": "GEUKCHIGO_DOKHAENG_1994",
        "focus": "geukchigo",
    },
    {
        "id": "FM-09",
        "title": "『東武遺稿‧知風兆』를 통해 본 이제마의 군사학적 배경",
        "authors": "JKMH",
        "year": 2019,
        "fetch": "koreascience",
        "jako_id": "JAKO201913661037959",
        "slug": "DONGMUYUGO_JIPUNGJO_2019",
        "focus": "dongmu_yugo",
    },
    {
        "id": "FM-11",
        "title": "사상의학 형성 과정 문헌적 고찰",
        "authors": "JSCIM",
        "year": 2020,
        "fetch": "jscim",
        "arti_id": "ART002804102",
        "slug": "SASANG_FORMATION_BIPAK_2020",
        "focus": "dongmu_yugo",
    },
    {
        "id": "FM-12",
        "title": "사상체질의학의 영원철학적 접근",
        "authors": "JSCIM",
        "year": 2019,
        "fetch": "jscim",
        "arti_id": "ART002453921",
        "slug": "JSCIM_JEMA_PHILOSOPHY_2019",
        "focus": "geukchigo",
    },
    {
        "id": "FM-13",
        "title": "동무 이제마와 노사 기정진의 만남",
        "authors": "JSCIM",
        "year": 2024,
        "fetch": "jscim",
        "arti_id": "ART003062945",
        "slug": "JSCIM_JEMA_GIJUNGJIN_2024",
        "focus": "bibliography",
    },
    {
        "id": "FM-10",
        "title": "한의학의 새로운 장을 개척",
        "authors": "JSCIM",
        "year": 2020,
        "fetch": "jscim",
        "arti_id": "ART002804041",
        "slug": "JSCIM_JEMA_OVERVIEW_2020",
        "focus": "bibliography",
    },
    {
        "id": "FM-14",
        "title": "조각대황탕(皂角大黃湯) 적용 병증의 형성과 처방구성의 변천에 관한 고찰",
        "authors": "JSCIM",
        "year": 2010,
        "fetch": "jscim",
        "arti_id": "ART002268334",
        "slug": "JOGak_DAEHWANGTANG_FORMATION_JSCIM",
        "focus": "dongmu_yugo",
    },
    {
        "id": "FM-15",
        "title": "사상의학에서 각 체질별 기운의 방향 특성",
        "authors": "JSCIM",
        "year": 2008,
        "fetch": "jscim",
        "arti_id": "ART001339588",
        "slug": "SASANG_KI_DIRECTION_JSCIM",
        "focus": "geukchigo",
    },
    {
        "id": "FM-16",
        "title": "동의보감과 동의수세보원을 중심으로 한 적하수오와 백하수오에 대한 고찰",
        "authors": "JSCIM",
        "year": 2025,
        "fetch": "jscim",
        "arti_id": "ART003266285",
        "slug": "HESHOUWU_DOB_DSSBW_JSCIM",
        "focus": "dongmu_yugo",
    },
]

MINE_TERMS = [
    "闡幽抄",
    "闡幽草",
    "闡幽",
    "천유초",
    "遺稿抄",
    "遺藁抄",
    "格致藁",
    "儒略",
    "反誠箴",
    "獨行篇",
    "東武遺稿",
    "知風兆",
    "四象草本",
    "동무유고",
    "격치고",
    "皂角",
    "大黃",
    "懋平",
    "務平",
    "白何首烏",
    "赤何首烏",
    "吸聚",
    "呼散",
]

LIST_MARKERS = ("목록", "著書", "刊行", "간행", "저술", "유서", "遺著", "전집", "著훔", "간행물")
QUOTE_MARKERS = ("「", "『", "」", "』", "引", "擇", "云", "曰")

EXA_QUERIES = [
    "이제마 格致藁 PDF site:medhist.or.kr OR site:journal.kci.go.kr",
    "이제마 東武遺稿 知風兆 PDF OR koreascience",
    "闡幽抄 이제마 民放 1997 OR 遺稿抄 전문",
    "박석언 格致藁 遺稿抄 NLK 199.1-이617",
    "이제마 학위논문 부록 천유초 OR 闡幽 site:riss.kr",
    "사상체질과 임상편람 闡幽草 p.344 OR 9788992971706",
]

CONTEXT = 120


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run(cmd: list[str]) -> tuple[int, str]:
    p = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or p.stderr)[-400:]


def _longest_hanja_run(text: str) -> int:
    runs = re.findall(r"[\u4e00-\u9fff]+", text)
    return max((len(r) for r in runs), default=0)


def classify_layer(term: str, snippet: str) -> str:
    """Never emit primary_hanja_chunk without human physical anchor."""
    hanja_run = _longest_hanja_run(snippet)
    cheonyu = term in ("闡幽抄", "천유초", "闡幽草", "闡幽")
    if cheonyu:
        if any(m in snippet for m in LIST_MARKERS) or len(snippet) < 140:
            return "list_mention"
        if hanja_run >= 25 and any(m in snippet for m in QUOTE_MARKERS):
            return "secondary_quote"
        return "list_mention"
    if hanja_run >= 35 or (hanja_run >= 20 and any(m in snippet for m in QUOTE_MARKERS)):
        return "secondary_quote"
    if any(m in snippet for m in LIST_MARKERS):
        return "list_mention"
    return "secondary_quote" if len(snippet) >= 180 else "list_mention"


def extract_pdf_text(path: Path) -> tuple[str, str]:
    try:
        from pdfminer.high_level import extract_text

        return extract_text(str(path)) or "", "pdfminer.six"
    except ImportError:
        pass
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        parts = [(page.extract_text() or "") for page in reader.pages]
        return "\n".join(parts), "pypdf"
    except ImportError:
        pass
    raise RuntimeError("Install pdfminer.six or pypdf")


def grep_snippets(text: str, terms: list[str]) -> dict[str, list[str]]:
    hits: dict[str, list[str]] = {}
    compact = re.sub(r"\s+", " ", text)
    for term in terms:
        snippets: list[str] = []
        for m in re.finditer(re.escape(term), compact, flags=re.IGNORECASE if term.isascii() is False else 0):
            start = max(0, m.start() - CONTEXT)
            end = min(len(compact), m.end() + CONTEXT)
            snip = compact[start:end].strip()
            if snip and snip not in snippets:
                snippets.append(snip)
            if len(snippets) >= 8:
                break
        if snippets:
            hits[term] = snippets
    return hits


def fetch_jscim(arti_id: str, dest: Path) -> str:
    if dest.is_file() and dest.stat().st_size > 10_000:
        return "cached"
    url = f"https://journal.kci.go.kr/JSCIM/archive/articlePdf?artiId={arti_id}"
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (MKM)", "Referer": "https://journal.kci.go.kr/"},
        )
        data = urllib.request.urlopen(req, timeout=60).read()
        if data[:4] == b"%PDF" and len(data) > 5000:
            dest.write_bytes(data)
            return "fetched_jscim"
        return f"jscim_not_pdf:{data[:40]!r}"
    except OSError as exc:
        return f"jscim_error:{exc}"


def ensure_target_pdf(target: dict) -> dict:
    row = {**target, "pdf_status": "pending"}
    slug = target["slug"]
    dest = RAW / f"{slug}_dr.pdf"
    if dest.is_file() and dest.stat().st_size > 10_000:
        row["pdf_status"] = "cached"
        row["pdf_path"] = str(dest.relative_to(ROOT)).replace("\\", "/")
        return row
    if target.get("fetch") == "jscim":
        row["pdf_status"] = fetch_jscim(target["arti_id"], dest)
    elif target.get("fetch") == "koreascience":
        code, tail = run(
            [
                sys.executable,
                "scripts/fetch_koreascience_pdf_v1.py",
                "--jako-id",
                target["jako_id"],
                "--slug",
                slug,
            ]
        )
        ks = RAW / f"{slug}_koreascience.pdf"
        if ks.is_file() and not dest.is_file():
            ks.rename(dest)
        row["pdf_status"] = "fetched_koreascience" if dest.is_file() else f"koreascience_fail:{code}"
        if code != 0:
            row["fetch_tail"] = tail
    elif target.get("fetch") == "direct_pdf":
        url = target["pdf_url"]
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (MKM)"})
            data = urllib.request.urlopen(req, timeout=60).read()
            if data[:4] == b"%PDF" and len(data) > 5000:
                dest.write_bytes(data)
                row["pdf_status"] = "fetched_direct"
            else:
                row["pdf_status"] = "direct_not_pdf"
        except OSError as exc:
            row["pdf_status"] = f"direct_error:{exc}"
    if dest.is_file() and dest.stat().st_size > 5000:
        row["pdf_path"] = str(dest.relative_to(ROOT)).replace("\\", "/")
    else:
        row["pdf_path"] = None
    return row


def collect_pdf_sources() -> list[dict]:
    sources: list[dict] = []
    seen: set[str] = set()

    if SECONDARY_MANIFEST.is_file():
        manifest = json.loads(SECONDARY_MANIFEST.read_text(encoding="utf-8"))
        for p in manifest.get("papers") or []:
            rel = p.get("pdf_path")
            if rel and rel not in seen:
                seen.add(rel)
                sources.append(
                    {
                        "source_id": p.get("id", "DR"),
                        "pdf_path": rel,
                        "citation": f"{p.get('authors','')} ({p.get('year','')}) {p.get('title','')[:50]}",
                        "focus": "secondary_corpus",
                    }
                )

    for t in TIER0_TARGETS:
        row = ensure_target_pdf(t)
        rel = row.get("pdf_path")
        if rel and rel not in seen:
            seen.add(rel)
            sources.append(
                {
                    "source_id": t["id"],
                    "pdf_path": rel,
                    "citation": f"{t.get('authors','')} ({t.get('year','')}) {t.get('title','')[:50]}",
                    "focus": t.get("focus", "fragment_mine"),
                    "fetch_status": row.get("pdf_status"),
                }
            )

    for pdf in sorted(RAW.glob("*.pdf")):
        rel = str(pdf.relative_to(ROOT)).replace("\\", "/")
        if rel in seen:
            continue
        name = pdf.name.lower()
        if any(k in name for k in ("jema", "ijeoma", "cheonyu", "kim_namil", "lee_kyung", "dongmu", "geukchi", "gyukchi", "sasang", "kjmh")):
            seen.add(rel)
            sources.append({"source_id": pdf.stem, "pdf_path": rel, "citation": pdf.stem, "focus": "raw_scan"})

    for proxy in sorted(RAW.glob("*_nl_proxy.md")):
        rel = str(proxy.relative_to(ROOT)).replace("\\", "/")
        if rel in seen:
            continue
        seen.add(rel)
        slug = proxy.name.replace("_nl_proxy.md", "")
        sources.append(
            {
                "source_id": f"NL-{slug}",
                "pdf_path": rel,
                "citation": f"NL proxy {slug}",
                "focus": "nl_proxy",
                "is_text_proxy": True,
            }
        )
    return sources


def mine_pdf(source: dict) -> list[dict]:
    if source.get("is_text_proxy"):
        path = ROOT / source["pdf_path"]
        if not path.is_file():
            return []
        text = path.read_text(encoding="utf-8", errors="replace")
        backend = "nl_proxy_md"
    else:
        pdf = ROOT / source["pdf_path"]
        if not pdf.is_file():
            return []
        try:
            text, backend = extract_pdf_text(pdf)
        except Exception as exc:  # noqa: BLE001 — artifact row
            return [
                {
                    "chunk_id": str(uuid.uuid4()),
                    "source_id": source["source_id"],
                    "pdf_path": source["pdf_path"],
                    "layer": "error",
                    "term": None,
                    "snippet": str(exc)[:200],
                    "citation": source.get("citation"),
                }
            ]

    term_hits = grep_snippets(text, MINE_TERMS)
    chunks: list[dict] = []
    for term, snippets in term_hits.items():
        for snip in snippets:
            layer = classify_layer(term, snip)
            chunks.append(
                {
                    "chunk_id": str(uuid.uuid4()),
                    "source_id": source["source_id"],
                    "pdf_path": source["pdf_path"],
                    "citation": source.get("citation"),
                    "focus": source.get("focus"),
                    "term": term,
                    "layer": layer,
                    "snippet": snip[:500],
                    "hanja_run_max": _longest_hanja_run(snip),
                    "text_backend": backend,
                    "physical_verified": False,
                    "canon_claim": False,
                }
            )
    return chunks


def exa_discover(*, num_results: int = 5) -> dict:
    api_key = os.environ.get("EXA_API_KEY", "").strip()
    meta: dict = {
        "schema": "cheonyucho_fragment_exa_discover_v1",
        "generated_at_utc": _utc(),
        "send_gate": "HOLD",
        "queries": EXA_QUERIES,
        "discoveries": [],
        "pdf_fetch_attempts": [],
        "status": "skipped_no_api_key",
    }
    if not api_key:
        return meta

    meta["status"] = "ok"
    for query in EXA_QUERIES:
        payload = {
            "query": query,
            "numResults": num_results,
            "type": "auto",
            "contents": {"text": {"maxCharacters": 800}},
        }
        try:
            req = urllib.request.Request(
                EXA_SEARCH_URL,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json", "x-api-key": api_key},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                doc = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.HTTPError, urllib.error.URLError, OSError) as exc:
            meta["discoveries"].append({"query": query, "error": str(exc)[:200]})
            continue

        for item in doc.get("results") or []:
            if not isinstance(item, dict):
                continue
            url = str(item.get("url") or "")
            title = str(item.get("title") or "")[:120]
            text = re.sub(r"\s+", " ", str(item.get("text") or item.get("summary") or ""))[:600]
            entry = {
                "query": query,
                "url": url,
                "title": title,
                "text_preview": text,
                "layer": "exa_discovery",
            }
            meta["discoveries"].append(entry)
            if url.lower().endswith(".pdf"):
                slug = re.sub(r"[^a-zA-Z0-9_]+", "_", url.split("/")[-1][:40])
                dest = RAW / f"exa_discover_{slug}.pdf"
                if not dest.is_file():
                    try:
                        req2 = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (MKM)"})
                        data = urllib.request.urlopen(req2, timeout=45).read()
                        if data[:4] == b"%PDF" and len(data) > 5000:
                            dest.write_bytes(data)
                            meta["pdf_fetch_attempts"].append({"url": url, "path": str(dest.relative_to(ROOT)), "ok": True})
                        else:
                            meta["pdf_fetch_attempts"].append({"url": url, "ok": False, "reason": "not_pdf"})
                    except OSError as exc:
                        meta["pdf_fetch_attempts"].append({"url": url, "ok": False, "reason": str(exc)[:120]})
    return meta


def summarize(chunks: list[dict]) -> dict:
    by_layer: dict[str, int] = {}
    by_term: dict[str, int] = {}
    cheonyu = 0
    geuk = 0
    dongmu = 0
    for c in chunks:
        layer = c.get("layer") or "unknown"
        term = c.get("term") or "?"
        by_layer[layer] = by_layer.get(layer, 0) + 1
        by_term[term] = by_term.get(term, 0) + 1
        if term in ("闡幽抄", "천유초", "闡幽草", "闡幽"):
            cheonyu += 1
        if term in ("格致藁", "儒略", "反誠箴", "獨行篇", "격치고"):
            geuk += 1
        if term in ("東武遺稿", "知風兆", "동무유고"):
            dongmu += 1
    return {
        "total_chunks": len(chunks),
        "by_layer": by_layer,
        "by_term_top": dict(sorted(by_term.items(), key=lambda x: -x[1])[:15]),
        "cheonyucho_chunks": cheonyu,
        "geukchigo_chunks": geuk,
        "dongmu_yugo_chunks": dongmu,
        "primary_hanja_chunk_count": by_layer.get("primary_hanja_chunk", 0),
    }


def main() -> int:
    # Refresh secondary corpus first (best-effort)
    run([sys.executable, "scripts/run_cheonyucho_secondary_corpus_dr_v1.py"])

    exa_meta = exa_discover()
    OUT_EXA_META.parent.mkdir(parents=True, exist_ok=True)
    OUT_EXA_META.write_text(json.dumps(exa_meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    sources = collect_pdf_sources()
    all_chunks: list[dict] = []
    for src in sources:
        all_chunks.extend(mine_pdf(src))

    summary = summarize(all_chunks)
    ledger = {
        "schema": "cheonyucho_fragment_ledger_v1",
        "generated_at_utc": _utc(),
        "track": "B",
        "send_gate": "HOLD",
        "canon_status": "not_acquired",
        "ssot_hanja": "闡幽抄",
        "priority_order": ["geukchigo", "dongmu_yugo", "cheonyucho"],
        "tier0_targets": TIER0_TARGETS,
        "pdf_sources": sources,
        "exa_discover_meta": str(OUT_EXA_META.relative_to(ROOT)).replace("\\", "/"),
        "exa_status": exa_meta.get("status"),
        "summary": summary,
        "chunks": all_chunks,
        "overclaim_firewall": {
            "primary_hanja_chunk_allowed": False,
            "physical_verified_default": False,
            "cheonyucho_fulltext_from_papers": False,
        },
        "reproduce": "py scripts/run_cheonyucho_fragment_mine_v1.py",
    }
    OUT_LEDGER.parent.mkdir(parents=True, exist_ok=True)
    OUT_LEDGER.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "ledger": str(OUT_LEDGER),
                "sources": len(sources),
                "chunks": len(all_chunks),
                "summary": summary,
                "exa_status": exa_meta.get("status"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
