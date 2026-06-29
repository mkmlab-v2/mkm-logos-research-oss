#!/usr/bin/env python3
"""T1 auto-fetch: bookstore metadata + RISS/NLK/encykorea for chobon 012 / cheonyucho — B-track HOLD."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "docs/research/raw"
OUT = ROOT / "reports/constitution/btrack_pilot/ijeoma_t1_toc_fetch_v1.json"
TIER = RAW / "IJEOMA_SECONDARY_SUBSTITUTE_TIER_v1.json"

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
HEADERS = {
    "User-Agent": UA,
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

TARGETS = [
    {
        "id": "T1-PARK-CHOBON-2003",
        "label": "박성식 동의수세보원 사상초본권 2003",
        "isbn": "9788930309769",
        "aladin_item_id": "406605",
        "kyobo_url": "https://product.kyobobook.co.kr/detail/S000000544679",
        "riss_query": "동의수세보원 사상초본권 박성식",
        "riss_mat_type": "d7345961987b50bf",
        "nlk_query": "동의수세보원 사상초본권",
        "grep_terms": ["천유초", "闡幽", "闡幽抄", "012.", "012번", "012 ", "第012", "012편"],
    },
    {
        "id": "T1-LEE-DONGMUYUGO-1999",
        "label": "이창일 東武遺稿 청계 1999",
        "isbn": "9788988473092",
        "aladin_item_id": None,
        "kyobo_url": None,
        "manual_toc_proxy": "docs/research/raw/T1-LEE-DONGMUYUGO-1999_kyobo_toc_manual_nl_proxy.md",
        "riss_query": "東武遺稿 이창일 1999",
        "riss_mat_type": "d7345961987b50bf",
        "nlk_query": "東武遺稿 이창일",
        "grep_terms": ["천유초", "闡幽", "闡幽抄", "011.", "011 ", "011. 천유", "012.", "012번"],
    },
    {
        "id": "T1-PARK-GEUKCHI-2001",
        "label": "지규용/이창일 격치고 역해 2001",
        "isbn": "9788985897310",
        "aladin_item_id": None,
        "kyobo_url": "https://product.kyobobook.co.kr/compare.jsp?isbn=9788985897310",
        "riss_query": "동무 격치고역해",
        "riss_mat_type": "d7345961987b50bf",
        "nlk_query": "동무 격치고",
        "grep_terms": ["천유초", "闡幽", "012.", "012번", "012 ", "第012"],
    },
]

ENCYKOREA = [
    {"id": "encykorea-E0045869", "article_id": "E0045869", "label": "이제마 encykorea"},
    {"id": "encykorea-E0073999", "article_id": "E0073999", "label": "김구익 encykorea"},
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_url(url: str, referer: str | None = None) -> tuple[str, int]:
    hdrs = dict(HEADERS)
    if referer:
        hdrs["Referer"] = referer
    req = urllib.request.Request(url, headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            return resp.read().decode("utf-8", "replace"), resp.status
    except OSError as exc:
        msg = str(exc)
        if "404" in msg:
            return "", 404
        return msg, -1


def extract_toc_lines(html: str) -> list[str]:
    lines: list[str] = []
    for pat in (
        r"(?:목차|차례|CONTENTS)[\s\S]{0,8000}?(?=<(?:div|section|footer)|$)",
        r'"tableOfContents"\s*:\s*"([^"]+)"',
        r'"description"\s*:\s*"([^"]{50,3000})"',
        r'id="toc[^"]*"[\s\S]{0,6000}?(?=</div>)',
    ):
        for m in re.finditer(pat, html, re.I):
            block = m.group(1) if m.lastindex else m.group(0)
            block = re.sub(r"<[^>]+>", "\n", block)
            block = re.sub(r"\\n", "\n", block)
            for ln in block.splitlines():
                t = re.sub(r"\s+", " ", ln).strip()
                if len(t) >= 2 and t not in lines:
                    lines.append(t)
    for m in re.finditer(r"(?:^|\n)\s*(0?\d{1,3})[\.\s]+([^\n<]{3,80})", html):
        title = re.sub(r"\s+", " ", m.group(2)).strip()
        if any(k in title for k in ("편", "장", "권", "篇", "幽", "초", "고", "론")):
            lines.append(f"{m.group(1)}. {title}")
    return lines[:120]


def meaningful_cheonyu_hits(gh: dict[str, list[str]]) -> dict[str, list[str]]:
    """Drop bare '012' and year false-positives (e.g. 2012)."""
    out: dict[str, list[str]] = {}
    for term, snips in gh.items():
        if term == "012":
            continue
        kept = []
        for s in snips:
            if term in ("012.", "012번", "012 ", "第012", "012편"):
                if "闡幽" in s or "천유" in s:
                    kept.append(s)
            elif "2012" in s and term in ("012.", "012 ", "012번"):
                continue
            else:
                kept.append(s)
        if kept:
            out[term] = kept
    return out


def grep_terms(text: str, terms: list[str]) -> dict[str, list[str]]:
    hits: dict[str, list[str]] = {}
    compact = re.sub(r"\s+", " ", text)
    for term in terms:
        snips: list[str] = []
        for m in re.finditer(re.escape(term), compact, re.I):
            start = max(0, m.start() - 80)
            end = min(len(compact), m.end() + 80)
            s = compact[start:end].strip()
            if s and s not in snips:
                snips.append(s)
            if len(snips) >= 5:
                break
        if snips:
            hits[term] = snips
    return meaningful_cheonyu_hits(hits)


def write_proxy(path: Path, title: str, url: str, body: str, toc: list[str], gh: dict) -> str:
    path.write_text(
        "\n".join(
            [
                f"# NL Proxy — {title}",
                f"**generated:** {_utc()} · research_only · send_gate: HOLD",
                f"**url:** {url}",
                "",
                "## TOC lines (extracted)",
                *[f"- {ln}" for ln in toc[:40]],
                "",
                "## Grep hits",
                json.dumps(gh, ensure_ascii=False, indent=2),
                "",
                "## Raw excerpt",
                body[:12000],
            ]
        ),
        encoding="utf-8",
    )
    return str(path.relative_to(ROOT)).replace("\\", "/")


def riss_hits(query: str, mat_type: str | None = None, limit: int = 5) -> list[dict]:
    params: dict[str, str] = {"query": query}
    if mat_type:
        params["p_mat_type"] = mat_type
    url = "https://www.riss.kr/search/Search.do?" + urllib.parse.urlencode(params)
    html, status = fetch_url(url)
    if status != 200:
        return [{"error": f"riss_status_{status}", "query": query}]
    hits: list[dict] = []
    for m in re.finditer(
        r'DetailView\.do\?[^"\']+control_no=([a-f0-9]+)[^"\']*["\'][^>]*>([^<]{4,120})<',
        html,
    ):
        hits.append(
            {
                "control_no": m.group(1),
                "title": re.sub(r"\s+", " ", m.group(2)).strip(),
                "detail_url": f"https://www.riss.kr/search/detail/DetailView.do?control_no={m.group(1)}",
            }
        )
        if len(hits) >= limit:
            break
    if not hits:
        for title in re.findall(r'class="title"[^>]*>([^<]+)<', html)[:limit]:
            t = re.sub(r"\s+", " ", title).strip()
            if t and t not in ("국내학술논문", "학위논문", "단행본", "기사"):
                hits.append({"title": t})
    return hits


def nlk_hits(query: str) -> list[dict]:
    url = "https://www.nl.go.kr/NL/contents/search.do?" + urllib.parse.urlencode({"kwd": query})
    html, status = fetch_url(url)
    if status != 200:
        return [{"error": f"nlk_status_{status}", "query": query}]
    hits: list[dict] = []
    for m in re.finditer(
        r'<a[^>]+detail_view_pop[^>]*>([^<]+)</a>.*?청구기호\s*:\s*([^\s<]+)',
        html,
        re.S,
    ):
        hits.append({"title": m.group(1).strip()[:160], "call_no": m.group(2).strip()})
    return hits[:8]


def fetch_aladin(isbn: str, item_id: str | None) -> dict:
    url = f"https://www.aladin.co.kr/shop/wproduct.aspx?ISBN={isbn}"
    html, status = fetch_url(url)
    row: dict = {"source": "aladin", "url": url, "status": status, "html_len": len(html)}
    if not html:
        row["note"] = "empty_html"
        return row
    m = re.search(r'ItemId=(\d+)', html)
    if m and not item_id:
        item_id = m.group(1)
    row["item_id"] = item_id
    title_m = re.search(r"<title>([^<]+)</title>", html, re.I)
    row["title_guess"] = title_m.group(1).strip() if title_m else None
    row["toc_line_count"] = 0
    row["toc_sample"] = []
    row["grep_hits"] = {}
    row["proxy_path"] = None
    row["note"] = "no_public_toc_in_html" if "목차" not in html and "차례" not in html else "toc_marker_present"
    return row


def fetch_bookstore_bundle(t: dict) -> list[dict]:
    rows: list[dict] = []
    if t.get("isbn"):
        al = fetch_aladin(t["isbn"], t.get("aladin_item_id"))
        html, _ = fetch_url(f"https://www.aladin.co.kr/shop/wproduct.aspx?ISBN={t['isbn']}")
        if html:
            toc = extract_toc_lines(html)
            gh = grep_terms(html, t["grep_terms"])
            al["toc_line_count"] = len(toc)
            al["toc_sample"] = toc[:25]
            al["grep_hits"] = gh
            proxy = RAW / f"{t['id']}_aladin_toc_nl_proxy.md"
            al["proxy_path"] = write_proxy(proxy, f"{t['id']} aladin", al["url"], html, toc, gh)
        rows.append(al)

    if t.get("kyobo_url"):
        html, status = fetch_url(t["kyobo_url"])
        toc = extract_toc_lines(html) if html else []
        gh = grep_terms(html, t["grep_terms"]) if html else {}
        row = {
            "source": "kyobo",
            "url": t["kyobo_url"],
            "status": status,
            "html_len": len(html),
            "toc_line_count": len(toc),
            "toc_sample": toc[:25],
            "grep_hits": gh,
            "proxy_path": None,
            "note": "bot_block_empty" if status == 200 and not html else None,
        }
        if html:
            proxy = RAW / f"{t['id']}_kyobo_toc_nl_proxy.md"
            row["proxy_path"] = write_proxy(proxy, f"{t['id']} kyobo", t["kyobo_url"], html, toc, gh)
        rows.append(row)
    return rows


def fetch_encykorea(entry: dict, grep: list[str]) -> dict:
    url = f"https://encykorea.aks.ac.kr/Article/{entry['article_id']}"
    html, status = fetch_url(url)
    gh = grep_terms(html, grep) if html else {}
    body_text = re.sub(r"<[^>]+>", " ", html) if html else ""
    body_text = re.sub(r"\s+", " ", body_text)
    proxy_path = None
    if html:
        proxy = RAW / f"{entry['id']}_encykorea_nl_proxy.md"
        proxy_path = write_proxy(proxy, entry["label"], url, body_text[:8000], [], gh)
    cheonyu_listed = "천유초" in html or "闡幽抄" in html
    chobon_listed = "초본권" in html or "四象草本卷" in html
    separate_work_snip = None
    if cheonyu_listed:
        m = re.search(r".{0,40}천유초.{0,120}", body_text)
        separate_work_snip = m.group(0).strip() if m else None
    return {
        "id": entry["id"],
        "label": entry["label"],
        "url": url,
        "status": status,
        "cheonyu_listed": cheonyu_listed,
        "chobon_listed": chobon_listed,
        "grep_hits": gh,
        "separate_work_snippet": separate_work_snip,
        "proxy_path": proxy_path,
        "classification": "separate_title_listed" if cheonyu_listed else "no_cheonyu_signal",
    }


def load_manual_toc_proxy(rel_path: str) -> dict | None:
    path = ROOT / rel_path.replace("/", "\\") if rel_path.startswith("docs") else RAW / rel_path
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8")
    toc: list[str] = []
    for ln in text.splitlines():
        s = ln.strip()
        if re.match(r"^(\*{0,2})?\d{1,3}\.", s) or "천유" in s or "011" in s:
            toc.append(re.sub(r"^\*+|\*+$", "", s).strip())
    gh = grep_terms(text, ["천유초", "闡幽", "011.", "011 ", "011. 천유"])
    has_011_cheonyu = any("천유" in ln for ln in toc) or "011. 천유" in text
    return {
        "source": "manual_kyobo_toc",
        "proxy_path": str(path.relative_to(ROOT)).replace("\\", "/"),
        "toc_line_count": len(toc),
        "toc_sample": toc[:25],
        "grep_hits": gh,
        "has_011_cheonyu": has_011_cheonyu,
        "note": "commander manual crossval — T1 only",
    }


def process_target(t: dict) -> dict:
    row: dict = {"id": t["id"], "label": t["label"], "fetches": []}
    combined = ""

    row["fetches"].extend(fetch_bookstore_bundle(t))

    manual = t.get("manual_toc_proxy")
    if manual:
        loaded = load_manual_toc_proxy(manual)
        if loaded:
            row["fetches"].append(loaded)
            combined += json.dumps(loaded.get("grep_hits", {}), ensure_ascii=False)

    riss = riss_hits(t["riss_query"], t.get("riss_mat_type"))
    row["fetches"].append({"source": "riss", "query": t["riss_query"], "mat_type": t.get("riss_mat_type"), "hits": riss})
    for h in riss:
        if h.get("detail_url"):
            dhtml, dst = fetch_url(h["detail_url"])
            combined += dhtml
            if dhtml:
                h["detail_status"] = dst
                h["grep_hits"] = grep_terms(dhtml, t["grep_terms"])
                h["has_cheonyu"] = "闡幽" in dhtml or "천유초" in dhtml

    nlk = nlk_hits(t["nlk_query"])
    row["fetches"].append({"source": "nlk", "query": t["nlk_query"], "hits": nlk})

    for f in row["fetches"]:
        if isinstance(f, dict) and f.get("grep_hits"):
            combined += json.dumps(f["grep_hits"], ensure_ascii=False)

    row["combined_grep"] = grep_terms(combined, t["grep_terms"])
    for f in row["fetches"]:
        if f.get("grep_hits"):
            for k, v in f["grep_hits"].items():
                row["combined_grep"].setdefault(k, []).extend(x for x in v if x not in row["combined_grep"].get(k, []))

    row["cheonyu_signal"] = bool(row["combined_grep"]) or any(
        f.get("has_cheonyu") or f.get("has_011_cheonyu") for f in row["fetches"] if isinstance(f, dict)
    )
    ch12 = row["combined_grep"]
    row["l3_chobon_012_verdict"] = (
        "confirmed_in_toc"
        if ch12
        and any(k.startswith("012") or k.startswith("第012") for k in ch12)
        and any("闡幽" in " ".join(v) or "천유" in " ".join(v) for v in ch12.values())
        else "toc_not_verified"
    )
    row["l3_dongmu_011_verdict"] = (
        "TOC_verified_T1_manual"
        if any(f.get("has_011_cheonyu") for f in row["fetches"] if isinstance(f, dict))
        else "toc_not_verified"
    )
    return row


def build_verdict(targets: list[dict], ency: list[dict]) -> dict:
    ency_ij = next((e for e in ency if e["id"] == "encykorea-E0045869"), {})
    chobon = next((t for t in targets if t["id"] == "T1-PARK-CHOBON-2003"), {})
    dongmu = next((t for t in targets if t["id"] == "T1-LEE-DONGMUYUGO-1999"), {})
    return {
        "l3_chobon_012": chobon.get("l3_chobon_012_verdict", "toc_not_verified"),
        "l3_dongmu_011": dongmu.get("l3_dongmu_011_verdict", "toc_not_verified"),
        "l3_dongmu_011_isbn": "9788988473092",
        "l3_dongmu_011_proxy": "docs/research/raw/T1-LEE-DONGMUYUGO-1999_kyobo_toc_manual_nl_proxy.md",
        "encykorea_separate_work": bool(ency_ij.get("cheonyu_listed")),
        "encykorea_snippet": ency_ij.get("separate_work_snippet"),
        "cheonyu_any_target": any(t.get("cheonyu_signal") for t in targets),
        "bookstore_toc_obtained": any(
            f.get("toc_line_count", 0) > 0
            for t in targets
            for f in t.get("fetches", [])
            if f.get("source") in ("aladin", "kyobo", "yes24", "manual_kyobo_toc")
        ),
        "canon_status": "not_acquired",
        "note": (
            "L3 dongmu 011 TOC verified T1 manual; chobon 012 separate; "
            "encykorea parallel listing compatible; [CANON] requires T0 anchor"
        ),
    }


def patch_tier(verdict: dict, artifact: str) -> None:
    if not TIER.is_file():
        return
    tier = json.loads(TIER.read_text(encoding="utf-8"))
    sec = tier.setdefault("user_synthesis_crossval", {}).setdefault("section_1_cheonyucho_chobon_012", {})
    sec["012_chapter"] = (
        "dongmu 1999 ISBN 9788988473092 manual TOC: 011.천유초 verified T1; "
        "chobon 012 separate track — toc_not_verified unless 박성식2003 fetch"
    )
    sec["dongmu_011_chapter"] = "TOC_verified_T1_manual — proxy T1-LEE-DONGMUYUGO-1999_kyobo_toc_manual_nl_proxy.md"
    sec["t1_fetch_verdict"] = verdict
    sec["t1_fetch_artifact"] = artifact
    sec["last_t1_fetch_utc"] = _utc()
    tier.setdefault("claim_7_four_layer_ssot", {})["L3"] = (
        "동무유고 1999 011.천유초 → TOC_verified_T1_manual; "
        "초본권 012 → separate/unresolved unless needed"
    )
    tier.pop("section_1_cheonyucho_chobon_012", None)
    tier["updated_at_utc"] = _utc()
    TIER.write_text(json.dumps(tier, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    ency_rows = [fetch_encykorea(e, ["천유초", "闡幽", "闡幽抄", "초본권", "012.", "012번", "第012"]) for e in ENCYKOREA]
    targets = [process_target(t) for t in TARGETS]
    artifact_rel = str(OUT.relative_to(ROOT)).replace("\\", "/")
    verdict = build_verdict(targets, ency_rows)

    results = {
        "schema": "ijeoma_t1_toc_fetch_v1",
        "generated_at_utc": _utc(),
        "track": "B",
        "send_gate": "HOLD",
        "automation_scope": {
            "auto": [
                "aladin/NLK/encykorea HTML scrape",
                "RISS OPAC (mat_type book)",
                "TOC grep + nl_proxy + fragment_mine",
            ],
            "not_auto": [
                "kyobo bot-blocked empty body (needs browser Tier 2)",
                "NLK digitized full text login",
                "paid ebook DRM",
                "장서각 실물 scan",
                "[CANON] bind",
            ],
        },
        "verdict": verdict,
        "encykorea": ency_rows,
        "targets": targets,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    proxies = list(RAW.glob("T1-*_*_toc_nl_proxy.md")) + list(RAW.glob("encykorea-*_encykorea_nl_proxy.md"))
    if proxies:
        p = subprocess.run(
            [sys.executable, "scripts/run_cheonyucho_fragment_mine_v1.py"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        results["fragment_mine"] = {"exit_code": p.returncode, "tail": (p.stdout or p.stderr)[-300:]}
        OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    patch_tier(verdict, artifact_rel)

    print(
        json.dumps(
            {
                "ok": True,
                "out": str(OUT),
                "l3": verdict.get("l3_dongmu_011"),
                "l3_chobon_012": verdict.get("l3_chobon_012"),
                "encykorea_separate": verdict.get("encykorea_separate_work"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
