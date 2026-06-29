#!/usr/bin/env python3
"""L2 catalog-merge grep: Heojun/Hwangdoyeon title-key vs Ijeoma — B-track HOLD."""

from __future__ import annotations

import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "docs/research/raw"
OUT = ROOT / "reports/constitution/btrack_pilot/cheonyucho_catalog_merge_probe_v1.json"
PROXY = RAW / "L2_CATALOG_MERGE_heojun_hwangdoyeon_nl_proxy.md"
CLAIM7 = RAW / "IJEOMA_CLAIM7_FINAL_VERDICT_v1.json"

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
HEADERS = {"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9"}

GREP_TERMS = ["천유", "闡幽", "제중신편", "유고초", "遺稿", "허준", "황도연", "이제마", "濟衆"]

ENCY_ARTICLES = [
    {
        "id": "ijeoma_E0045869",
        "article_id": "E0045869",
        "label": "이제마",
        "role": "positive_attribution",
    },
    {
        "id": "heojun_E0063152",
        "article_id": "E0063152",
        "label": "허준",
        "role": "negative_control",
    },
    {
        "id": "geukchigo_E0066180",
        "article_id": "E0066180",
        "label": "격치고(格致藁)",
        "role": "appendix_title_collision",
    },
    {
        "id": "jijeongsinpyeon_E0051478",
        "article_id": "E0051478",
        "label": "제중신편(濟衆新編)",
        "role": "hwangdoyeon_court_work",
    },
]

NLK_QUERIES = [
    ("cheonyu_ijeoma", "천유초 이제마"),
    ("cheonyu_hanja", "闡幽抄"),
    ("heojun_cheonyu", "허준 천유"),
    ("hwang_jijeong", "황도연 제중신편"),
]


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


def grep_contexts(text: str, terms: list[str], *, window: int = 90) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for term in terms:
        hits: list[str] = []
        start = 0
        while len(hits) < 3:
            i = text.find(term, start)
            if i < 0:
                break
            snip = text[max(0, i - window) : i + window].strip()
            if snip and snip not in hits:
                hits.append(snip)
            start = i + len(term)
        if hits:
            out[term] = hits
    return out


def fetch_ency_article(entry: dict) -> dict:
    url = f"https://encykorea.aks.ac.kr/Article/{entry['article_id']}"
    try:
        html, status = fetch_url(url)
    except OSError as exc:
        return {"id": entry["id"], "url": url, "error": str(exc)}
    text = strip_html(html)
    gh = grep_contexts(text, GREP_TERMS)
    has_cheonyu = "천유" in text or "闡幽" in text
    has_jijeong = "제중신편" in text or "濟衆" in text
    has_yugo = "유고초" in text or "遺稿" in text
    return {
        "id": entry["id"],
        "label": entry["label"],
        "role": entry["role"],
        "url": url,
        "status": status,
        "has_cheonyu": has_cheonyu,
        "has_jijeongsinpyeon": has_jijeong,
        "has_yugochao": has_yugo,
        "grep_hits": gh,
        "grep_term_count": len(gh),
    }


def nlk_search(query: str) -> dict:
    import urllib.parse

    url = "https://www.nl.go.kr/NL/contents/search.do?" + urllib.parse.urlencode({"kwd": query})
    try:
        html, status = fetch_url(url)
    except OSError as exc:
        return {"query": query, "error": str(exc)}
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
        hits.append(
            {
                "title": title[:160],
                "call_no": call_no,
                "year": pub_year.group(1) if pub_year else None,
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
    body_cheonyu = html.count("천유") + html.count("闡幽")
    body_heojun = html.count("허준")
    body_hwang = html.count("황도연")
    return {
        "query": query,
        "status": status,
        "hit_count": len(uniq),
        "hits": uniq[:8],
        "page_term_counts": {
            "cheonyu_hanja": body_cheonyu,
            "heojun": body_heojun,
            "hwangdoyeon": body_hwang,
        },
    }


def synthesize_l2_verdict(ency: list[dict], nlk: dict[str, dict]) -> dict:
    ijeoma = next((e for e in ency if e.get("id") == "ijeoma_E0045869"), {})
    heojun = next((e for e in ency if e.get("id") == "heojun_E0063152"), {})
    geuk = next((e for e in ency if e.get("id") == "geukchigo_E0066180"), {})
    jij = next((e for e in ency if e.get("id") == "jijeongsinpyeon_E0051478"), {})
    heojun_nlk = nlk.get("heojun_cheonyu", {})
    cheonyu_nlk = nlk.get("cheonyu_ijeoma", {})

    mechanisms: list[str] = []
    if ijeoma.get("has_cheonyu"):
        mechanisms.append("encykorea_ijeoma_lists_cheonyucho")
    if heojun and not heojun.get("has_cheonyu"):
        mechanisms.append("encykorea_heojun_no_cheonyu_negative_control")
    if geuk.get("has_jijeongsinpyeon") and geuk.get("has_yugochao"):
        mechanisms.append("geukchigo_appendix_jijeongsinpyeon_yugochao_collision_keys")
    if jij.get("has_jijeongsinpyeon") and not jij.get("has_cheonyu"):
        mechanisms.append("jijeongsinpyeon_court_compilation_not_cheonyucho")
    if heojun_nlk.get("hit_count", 0) == 0:
        mechanisms.append("nlk_heojun_cheonyu_zero_hits")
    if cheonyu_nlk.get("hit_count", 0) > 0:
        mechanisms.append("nlk_cheonyu_ijeoma_positive_hits")

    supported = (
        ijeoma.get("has_cheonyu")
        and not heojun.get("has_cheonyu")
        and geuk.get("has_jijeongsinpyeon")
        and geuk.get("has_yugochao")
        and heojun_nlk.get("hit_count", 0) == 0
    )
    return {
        "L2_catalog_merge": "TRUE_at_T1" if supported else "partial",
        "mechanism_signals": mechanisms,
        "misattribution_hypothesis": (
            "제중신편(황도연/내의원) 키와 격치고 부록(제중신편·유고초) 키가 "
            "전산·2차 서지에서 이제마 闡幽抄와 병합·오분류될 수 있음; "
            "허준 전기(encykorea)에는 천유/闡幽 미등재"
        ),
    }


def write_proxy(doc: dict, ency: list[dict], nlk: dict[str, dict], verdict: dict) -> None:
    lines = [
        "# NL Proxy — L2 catalog-merge (Heojun · Hwangdoyeon · title-key collision)",
        "",
        f"**generated:** {_utc()} · `research_only` · `send_gate: HOLD`",
        f"**artifact:** `{OUT.relative_to(ROOT).as_posix()}`",
        "",
        "## L2 verdict (T1 secondary)",
        "",
        f"- **L2_catalog_merge:** `{verdict['L2_catalog_merge']}`",
        f"- **mechanisms:** {', '.join(verdict['mechanism_signals'])}",
        f"- **note:** {verdict['misattribution_hypothesis']}",
        "",
        "## encykorea grep",
        "",
    ]
    for e in ency:
        if e.get("error"):
            lines.append(f"### {e.get('id')} — ERROR")
            lines.append(f"- {e['error']}")
            continue
        lines.append(f"### {e['label']} ({e['id']})")
        lines.append(f"- url: {e['url']}")
        lines.append(
            f"- cheonyu={e.get('has_cheonyu')} jijeong={e.get('has_jijeongsinpyeon')} "
            f"yugochao={e.get('has_yugochao')}"
        )
        for term, ctxs in (e.get("grep_hits") or {}).items():
            lines.append(f"- **{term}:** {ctxs[0][:220]}")
        lines.append("")

    lines.extend(["## NLK search", ""])
    for key, row in nlk.items():
        lines.append(f"### {key} — query `{row.get('query')}`")
        lines.append(f"- hit_count: {row.get('hit_count', 0)} · page_terms: {row.get('page_term_counts')}")
        for h in row.get("hits", [])[:3]:
            lines.append(f"- {h.get('title')} | {h.get('call_no')} | {h.get('year')}")
        lines.append("")

    lines.extend(
        [
            "## Reproduce",
            "",
            "```powershell",
            "py scripts/run_cheonyucho_catalog_merge_probe_v1.py",
            "py scripts/run_cheonyucho_fragment_mine_v1.py",
            "```",
            "",
        ]
    )
    PROXY.write_text("\n".join(lines), encoding="utf-8")


def patch_claim7(artifact_rel: str, proxy_rel: str, verdict: dict) -> None:
    if not CLAIM7.is_file():
        return
    data = json.loads(CLAIM7.read_text(encoding="utf-8"))
    gaps = data.get("workspace_crossval", {}).get("workspace_gaps", [])
    data["workspace_crossval"]["workspace_gaps"] = [
        g for g in gaps if "L2_heojun_hwangdoyeon" not in g
    ]
    data["generated_at_utc"] = _utc()
    l2 = data.get("four_layer_final", {}).get("L2_catalog_merge_heojun_hwangdoyeon", {})
    l2["workspace_status"] = "grep_artifact_supported"
    l2["was"] = "[HYPO]"
    ev = list(l2.get("evidence", []))
    for item in (artifact_rel, proxy_rel, "encykorea E0045869/E0063152/E0066180/E0051478"):
        if item not in ev:
            ev.append(item)
    l2["evidence"] = ev
    l2["caveat"] = (
        "T1 archive URL grep 완료; T0 한자 primary 미취득 · "
        "황도연=제중신편 court 키 충돌 · 허준=천유 미등재 negative control"
    )
    l2["artifact"] = artifact_rel
    l2["grep_verdict"] = verdict
    data["four_layer_final"]["L2_catalog_merge_heojun_hwangdoyeon"] = l2
    CLAIM7.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    ency = [fetch_ency_article(e) for e in ENCY_ARTICLES]
    nlk = {key: nlk_search(q) for key, q in NLK_QUERIES}
    verdict = synthesize_l2_verdict(ency, nlk)
    doc = {
        "schema": "cheonyucho_catalog_merge_probe_v1",
        "generated_at_utc": _utc(),
        "send_gate": "HOLD",
        "track": "B",
        "encykorea": ency,
        "nlk": nlk,
        "l2_verdict": verdict,
        "proxy_path": str(PROXY.relative_to(ROOT)).replace("\\", "/"),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_proxy(doc, ency, nlk, verdict)
    artifact_rel = str(OUT.relative_to(ROOT)).replace("\\", "/")
    proxy_rel = str(PROXY.relative_to(ROOT)).replace("\\", "/")
    patch_claim7(artifact_rel, proxy_rel, verdict)
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(OUT),
                "proxy": str(PROXY),
                "L2": verdict["L2_catalog_merge"],
                "signals": len(verdict["mechanism_signals"]),
            },
            ensure_ascii=False,
        )
    )
    return 0 if verdict["L2_catalog_merge"] == "TRUE_at_T1" else 1


if __name__ == "__main__":
    raise SystemExit(main())
