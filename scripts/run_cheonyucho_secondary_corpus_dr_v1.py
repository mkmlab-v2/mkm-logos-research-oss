#!/usr/bin/env python3
"""Deep-research Tier 1+2: fetch OA papers + grep 闡幽/천유초 → secondary corpus manifest."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "docs/research/raw"
OUT_MANIFEST = RAW / "CHEONYUCHO_SECONDARY_CORPUS_v1.json"
OUT_LIT = ROOT / "docs/research/CHEONYUCHO_SECONDARY_CORPUS_MERGED_LIT_REVIEW_2026-06-24.md"
GREP_DIR = ROOT / "reports/constitution/btrack_pilot"

# Curated OA targets (medhist # or KCI artiId)
PAPERS: list[dict] = [
    {
        "id": "DR-01",
        "title": "이제마의 의학론과 그 시대적 성격",
        "authors": "이경록",
        "year": 2005,
        "fetch": "existing",
        "pdf": "docs/research/raw/LEE_KYUNGLOCK_2005_JEMA_MEDICAL_THEORY_kjmh-14-2-79.pdf",
        "url": "https://www.medhist.or.kr/journal/view.php?number=2139",
    },
    {
        "id": "DR-02",
        "title": "醫書의 刊行을 중심으로 살펴본 日帝時代 韓醫學의 학술적 경향",
        "authors": "김남일",
        "year": 2006,
        "fetch": "medhist",
        "medhist_number": 2131,
        "slug": "KIM_NAMIL_2006_HANUISAHYEJI",
    },
    {
        "id": "DR-03",
        "title": "동의수세보원사상초본권과 동무유고에서의 소증에 관한 고찰",
        "authors": "사상체질의학회",
        "year": 2000,
        "fetch": "jscim",
        "arti_id": "ART002709248",
        "slug": "SASANG_CHOBON_DONGMUYUGO_2000",
    },
    {
        "id": "DR-04",
        "title": "동무유고 약성가에 대한 연구",
        "authors": "박성식",
        "year": 2001,
        "fetch": "jscim",
        "arti_id": "ART002713144",
        "slug": "DONGMUYUGO_YAKSEONGGA_2001",
    },
    {
        "id": "DR-06",
        "title": "이제마 동의수세보원 의학·의사학적 관점",
        "authors": "이기복",
        "year": 2016,
        "fetch": "direct_pdf",
        "pdf_url": "https://www.medhist.or.kr/upload/pdf/kjmh-25-3-329.pdf",
        "slug": "LEE_GIBOK_2016_DSSBW_MEDHIST",
    },
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run(cmd: list[str]) -> tuple[int, str]:
    p = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or p.stderr)[-400:]


def ensure_pdf(paper: dict) -> dict:
    row = {**paper, "pdf_status": "pending"}
    if paper.get("fetch") == "existing":
        rel = paper["pdf"]
        path = ROOT / rel.replace("/", "\\")
        row["pdf_path"] = rel if path.is_file() else None
        row["pdf_status"] = "ok" if path.is_file() else "missing"
        row["slug"] = paper.get("slug") or "lee2005_jema_medical_theory"
        return row

    slug = paper["slug"]
    dest = RAW / f"{slug}_dr.pdf"
    if dest.is_file() and dest.stat().st_size > 10_000:
        row["pdf_path"] = str(dest.relative_to(ROOT)).replace("\\", "/")
        row["pdf_status"] = "cached"
        return row

    if paper.get("fetch") == "medhist":
        code, tail = run(
            [
                sys.executable,
                "scripts/fetch_medhist_pdf_v1.py",
                "--number",
                str(paper["medhist_number"]),
                "--slug",
                slug,
            ]
        )
        # fetch script writes to *_medhist.pdf
        alt = RAW / f"{slug}_medhist.pdf"
        if alt.is_file():
            if not dest.is_file():
                alt.rename(dest)
            row["pdf_path"] = str(dest.relative_to(ROOT)).replace("\\", "/")
            row["pdf_status"] = "fetched" if code == 0 else "fetched_with_warn"
        else:
            row["pdf_status"] = f"fetch_fail:{code}"
            row["fetch_tail"] = tail
        return row

    if paper.get("fetch") == "jscim":
        arti = paper["arti_id"]
        url = f"https://journal.kci.go.kr/JSCIM/archive/articlePdf?artiId={arti}"
        try:
            import urllib.request

            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (MKM)", "Referer": "https://journal.kci.go.kr/"},
            )
            data = urllib.request.urlopen(req, timeout=60).read()
            if data[:4] == b"%PDF" and len(data) > 5000:
                dest.write_bytes(data)
                row["pdf_path"] = str(dest.relative_to(ROOT)).replace("\\", "/")
                row["pdf_status"] = "fetched_jscim"
            else:
                row["pdf_status"] = "jscim_not_pdf"
                row["jscim_head"] = data[:80].decode("utf-8", "replace")
        except OSError as exc:
            row["pdf_status"] = f"jscim_error:{exc}"
        return row

    if paper.get("fetch") == "direct_pdf":
        url = paper["pdf_url"]
        try:
            import urllib.request

            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (MKM)"})
            data = urllib.request.urlopen(req, timeout=60).read()
            if data[:4] == b"%PDF" and len(data) > 5000:
                dest.write_bytes(data)
                row["pdf_path"] = str(dest.relative_to(ROOT)).replace("\\", "/")
                row["pdf_status"] = "fetched_direct"
            else:
                row["pdf_status"] = "direct_not_pdf"
        except OSError as exc:
            row["pdf_status"] = f"direct_error:{exc}"
        return row

    row["pdf_status"] = "unknown_fetch"
    return row


def grep_pdf(paper: dict) -> dict:
    rel = paper.get("pdf_path")
    if not rel:
        return {**paper, "grep_status": "skip_no_pdf"}
    slug = paper.get("slug") or paper["id"].lower().replace("-", "_")
    out = GREP_DIR / f"{slug}_grep_cheonyucho_v1.json"
    code, tail = run(
        [
            sys.executable,
            "scripts/grep_cheonyucho_pdf_v1.py",
            "--pdf",
            rel,
            "--out",
            str(out.relative_to(ROOT)),
            "--citation",
            f"{paper.get('authors','')} {paper.get('year','')} {paper.get('title','')[:40]}",
        ]
    )
    grep_doc = {}
    if out.is_file():
        grep_doc = json.loads(out.read_text(encoding="utf-8"))
    return {
        **paper,
        "grep_status": "ok" if code == 0 else f"grep_fail:{code}",
        "grep_artifact": str(out.relative_to(ROOT)).replace("\\", "/"),
        "cheonyucho_in_pdf": grep_doc.get("cheonyucho_in_pdf"),
        "verdict": grep_doc.get("verdict"),
        "term_hits_keys": list((grep_doc.get("term_hits") or {}).keys()),
    }


def write_lit_review(manifest: dict) -> None:
    lines = [
        "# 천유초(闡幽抄) — Secondary Corpus MERGED LIT_REVIEW (원전 없이)",
        "",
        f"**generated:** {manifest['generated_at_utc'][:10]} · `send_gate: HOLD` · `research_only`",
        "",
        "**Supersedes for SSOT (secondary-only path):** `docs/research/CHEONYUCHO_JEMA_MERGED_LIT_REVIEW_2026-06-24.md` 부록",
        "",
        "## Executive verdict",
        "",
        "- **원전 전문 대체:** 불가 — 논문·2차 판본으로 **서지·형성사·인용망**만 구축",
        "- **한자 SSOT:** 闡幽抄 (抄) — 임상편람 목차 闡幽草(草)는 실물 전 `UNVERIFIED`",
        "- **천유초 전문 부록:** 학위논문 스윕 **미발견** (`CHEONYUCHO_APPENDIX_BIBLIO_SWEEP_v1.json`)",
        "",
        "## Paper catalog (OA fetch + grep)",
        "",
        "| ID | 연도 | 저자 | PDF | 闡幽/천유초 | verdict |",
        "|----|------|------|-----|------------|---------|",
    ]
    for p in manifest["papers"]:
        flag = "Y" if p.get("cheonyucho_in_pdf") else ("—" if p.get("grep_status", "").startswith("skip") else "N")
        pdf = p.get("pdf_path") or "—"
        lines.append(
            f"| {p['id']} | {p.get('year','')} | {p.get('authors','')} | `{pdf}` | {flag} | {p.get('verdict','')} |"
        )

    lines.extend(
        [
            "",
            "## Reconstruction strategy (B-track)",
            "",
            "1. **서지 노드:** 김남일 2006 + 이경록 2005 — 闡幽抄 **목록·간행**",
            "2. **형성사:** 사상초본권 + 동무유고 (DR-03~05) — 천유초 이전·병행 사유",
            "3. **격치고·유고초:** 별권; 동일시 `[HYPO]` 금지",
            "4. **Human P1:** 장서각/NLK 闡幽抄 원전 — `[CANON]` 해제 조건",
            "",
            "## Overclaim firewall",
            "",
            "- 금지: 「천유초 전문 확보」·유고초=천유초 동일시·Track A 승격",
            "- 허용: PAPER_PROXY 인용망 · NL 연구 레이어 · send_gate HOLD",
            "",
            "## Reproduce",
            "",
            "```powershell",
            "py scripts/run_cheonyucho_secondary_corpus_dr_v1.py",
            "py scripts/run_cheonyucho_auto_chain_v1.py",
            "```",
            "",
            f"Manifest: `{OUT_MANIFEST.relative_to(ROOT).as_posix()}`",
        ]
    )
    OUT_LIT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    rows = [grep_pdf(ensure_pdf(p)) for p in PAPERS]
    cheonyu_hits = [p for p in rows if p.get("cheonyucho_in_pdf")]
    manifest = {
        "schema": "cheonyucho_secondary_corpus_v1",
        "generated_at_utc": _utc(),
        "track": "B",
        "send_gate": "HOLD",
        "canon_status": "not_acquired",
        "ssot_hanja": "闡幽抄",
        "strategy": "secondary_corpus_without_primary_fulltext",
        "primary_fulltext_substitute": False,
        "papers": rows,
        "cheonyucho_mention_count": len(cheonyu_hits),
        "cheonyucho_mention_ids": [p["id"] for p in cheonyu_hits],
        "appendix_sweep": "docs/research/raw/CHEONYUCHO_APPENDIX_BIBLIO_SWEEP_v1.json",
        "reproduce": "py scripts/run_cheonyucho_secondary_corpus_dr_v1.py",
    }
    OUT_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    OUT_MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_lit_review(manifest)

    # patch biblio sweep pointer
    bib = ROOT / "docs/research/raw/CHEONYUCHO_JEMA_BIBLIO_SWEEP_v1.json"
    if bib.is_file():
        b = json.loads(bib.read_text(encoding="utf-8"))
        b["secondary_corpus"] = str(OUT_MANIFEST.relative_to(ROOT)).replace("\\", "/")
        b["secondary_merged_lit_review"] = str(OUT_LIT.relative_to(ROOT)).replace("\\", "/")
        bib.write_text(json.dumps(b, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "manifest": str(OUT_MANIFEST),
                "lit_review": str(OUT_LIT),
                "pdfs": sum(1 for p in rows if p.get("pdf_path")),
                "cheonyucho_hits": len(cheonyu_hits),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
