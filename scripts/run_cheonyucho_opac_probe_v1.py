#!/usr/bin/env python3
"""OPAC/RISS probe for cheonyucho P1 — Park 1985 + 사상체질과 임상편람."""

from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports/constitution/btrack_pilot/cheonyucho_opac_probe_v1.json"
CARD = ROOT / "reports/constitution/btrack_pilot/cheonyucho_p1_library_request_card_v1.txt"

QUERIES = [
    ("park1985", "동무격치고 박석언 1985"),
    ("park1985_hanja", "格致藁 박석언 1985"),
    ("sasang_clinical", "사상체질과 임상편람"),
    ("sasang_isbn_vol1", "9788992971690"),
    ("sasang_isbn_vol2", "9788992971706"),
    ("cheonyucho_nlk", "闡幽抄 이제마"),
    ("cheonyucho_ko", "천유초 이제마"),
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def riss_search(query: str, limit: int = 5) -> list[dict]:
    url = "https://www.riss.kr/search/Search.do?" + urllib.parse.urlencode({"query": query})
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
    hits: list[dict] = []
    # title blocks near DetailView links
    for m in re.finditer(
        r'DetailView\.do\?[^"\']+control_no=([a-f0-9]+)[^"\']*["\'][^>]*>([^<]{4,120})<',
        html,
    ):
        hits.append(
            {
                "control_no": m.group(1),
                "title_guess": re.sub(r"\s+", " ", m.group(2)).strip(),
                "detail_url": f"https://www.riss.kr/search/detail/DetailView.do?control_no={m.group(1)}",
            }
        )
        if len(hits) >= limit:
            break
    if not hits:
        for title in re.findall(r'class="title"[^>]*>([^<]+)<', html)[:limit]:
            t = re.sub(r"\s+", " ", title).strip()
            if t and t not in ("국내학술논문", "학위논문", "단행본"):
                hits.append({"title_guess": t})
    return hits


def riss_detail(control_no: str, mat_type: str = "d7345961987b50bf") -> dict:
    url = (
        f"https://www.riss.kr/search/detail/DetailView.do?"
        f"p_mat_type={mat_type}&control_no={control_no}"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
    meta: dict[str, str] = {}
    for m in re.finditer(r'<meta\s+name="([^"]+)"\s+content="([^"]*)"', html):
        meta[m.group(1)] = m.group(2).strip()
    isbns = re.findall(r"978[0-9\-]{10,17}", html)
    call_nos = re.findall(r"[0-9]{3}\.[0-9]{2}-[0-9]{2}", html)
    return {
        "url": url,
        "meta": meta,
        "isbn": list(dict.fromkeys(isbns))[:5],
        "call_no_guess": call_nos[:3],
        "has_cheonyu": "闡幽" in html or "천유초" in html,
        "has_geukchigo": "格致" in html or "격치고" in html,
    }


def build_library_card(probe: dict) -> str:
    sasang = probe.get("sasang_clinical", {})
    park = probe.get("park1985", {})
    lines = [
        "=== MKM P1 도서관 청구 카드 (천유초·격치고) ===",
        "send_gate: HOLD | research_only | physical_verified: false",
        "",
        "[우선순위 1] 사상체질과 임상편람 2 — p.344 闡幽草/抄 (vol.2 우선)",
        "  제목: 사상체질과 임상편람 2 - 사상의학 문헌집 (추정)",
        "  출판: 한미의학, 2010",
        "  ISBN vol.2: 9788992971706 | vol.1: 9788992971690 (~217쪽 [HYPO], p.344 불가)",
        "  RISS vol.2: https://www.riss.kr/search/detail/DetailView.do?control_no=8774e49918c01006ffe0bdc3ef48d419",
        "  NLK: 519.74-10-4-1-2 (사상체질과 임상편람. 1-2)",
        "  확인 요청: p.344 한자 草/抄 · 천유초 전문 유무 · 遺稿抄와 별권 여부",
        "",
        "[우선순위 2] 동무격치고 박석언 역주 (태양사, 1985)",
        "  원저: 이제마(李濟馬) | 역주: 박석언 | 출판: 태양사, 1985-10-25 (encykorea E0066180)",
        "  확인 요청: 뒤색인·각주에 闡幽抄·천유초·遺稿抄 grep",
        "  NLK 검색: https://www.nl.go.kr/NL/contents/search.do?kwd=동무격치고",
        "  RISS: '동무격치고 박석언' 직접 단행본 히트 약함 — 상호대차(책바래)로 태양사판 요청 권장",
    ]
    lines.append("  RISS 직접 히트: 약함 (논문·타판본 위주)")
    lines.extend(
        [
            "",
            "[우선순위 3] 장서각 JSG",
            "  URL: https://jsg.aks.ac.kr/ — 검색어: 格致藁, 闡幽抄, 遺稿抄",
            "  known: JSG_K3-328 동의수세보원만 확인됨",
            "",
            "재현: py scripts/run_cheonyucho_opac_probe_v1.py",
            f"생성: {_utc()}",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    results: dict[str, object] = {"schema": "cheonyucho_opac_probe_v1", "generated_at_utc": _utc()}
    for key, q in QUERIES:
        try:
            hits = riss_search(q)
            entry: dict[str, object] = {"query": q, "riss_hits": hits}
            if hits and hits[0].get("control_no"):
                try:
                    entry["detail"] = riss_detail(hits[0]["control_no"])
                except OSError as exc:
                    entry["detail_error"] = str(exc)
            results[key] = entry
        except OSError as exc:
            results[key] = {"query": q, "error": str(exc)}

    # enrich known sasang record
    try:
        results["sasang_clinical_known"] = riss_detail("ee076abcbb30b5b8ffe0bdc3ef48d419")
    except OSError as exc:
        results["sasang_clinical_known_error"] = str(exc)

    results["nlk_manual_urls"] = {
        "search_park1985": "https://www.nl.go.kr/NL/contents/search.do?kwd=동무격치고",
        "search_sasang": "https://www.nl.go.kr/NL/contents/search.do?kwd=사상체질과+임상편람",
        "search_cheonyucho": "https://www.nl.go.kr/NL/contents/search.do?kwd=천유초",
        "note": "NLK openApi requires key; UI search for commander",
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # Library card SSOT: cheonyucho_p1_library_request_card_v1.txt (원전 P1) — do not overwrite here.

    # update probe checklist P1-03
    probe_path = ROOT / "reports/constitution/btrack_pilot/cheonyucho_acquisition_probe_v1.json"
    if probe_path.is_file():
        probe = json.loads(probe_path.read_text(encoding="utf-8"))
        for item in probe.get("checklist", []):
            if item["id"] == "P1-03":
                item["status"] = "opac_probe_run"
                item["artifact"] = str(OUT.relative_to(ROOT)).replace("\\", "/")
                item["library_card"] = str(CARD.relative_to(ROOT)).replace("\\", "/")
            if item["id"] == "P1-01":
                item["opac_artifact"] = str(OUT.relative_to(ROOT)).replace("\\", "/")
        probe["updated_at_utc"] = _utc()
        probe_path.write_text(json.dumps(probe, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    park_hits = len((results.get("park1985") or {}).get("riss_hits", []))  # type: ignore[union-attr]
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(OUT),
                "card": str(CARD),
                "park1985_hits": park_hits,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
