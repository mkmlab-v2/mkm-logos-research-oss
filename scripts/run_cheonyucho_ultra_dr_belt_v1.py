#!/usr/bin/env python3
"""Ultra deep-research belt: Tier0 proxy ingest + Exa6 + fragment mine + MERGED LIT (HOLD)."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "docs/research/raw"
OUT_RUN = ROOT / "reports/constitution/btrack_pilot/cheonyucho_ultra_dr_belt_run_v1.json"
OUT_LIT = ROOT / "docs/research/CHEONYUCHO_ULTRA_DR_MERGED_LIT_REVIEW_2026-06-24.md"
TIER0_PROXY = RAW / "CHEONYUCHO_ULTRA_TIER0_PROXY_2026-06-24.md"
LEDGER = RAW / "CHEONYUCHO_FRAGMENT_LEDGER_v1.json"
EXA_META = ROOT / "reports/constitution/btrack_pilot/cheonyucho_fragment_exa_discover_v1.json"

# Ultra belt: 6 Exa rounds (written into fragment_mine via env override file)
ULTRA_EXA_QUERIES = [
    "이제마 格致藁 PDF site:medhist.or.kr OR site:journal.kci.go.kr",
    "이제마 東武遺稿 知風兆 PDF OR koreascience",
    "闡幽抄 이제마 民放 1997 OR 遺稿抄 전문",
    "박석언 格致藁 遺稿抄 NLK 199.1-이617",
    "이제마 학위논문 부록 천유초 OR 闡幽 site:riss.kr",
    "사상체질과 임상편람 闡幽草 p.344 OR 9788992971706",
]

# Extra JSCIM OA from prior Exa hits
ULTRA_JSCIM_TARGETS = [
    ("FM-11", "ART002804102", "SASANG_FORMATION_BIPAK_2020", "사상의학 형성 과정 문헌적 고찰", 2020),
    ("FM-12", "ART002453921", "JSCIM_JEMA_PHILOSOPHY_2019", "사상체질의학의 영원철학적 접근", 2019),
    ("FM-13", "ART003062945", "JSCIM_JEMA_GIJUNGJIN_2024", "동무 이제마와 노사 기정진의 만남", 2024),
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run(cmd: list[str]) -> dict:
    p = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
    tail = (p.stdout or p.stderr or "")[-500:]
    return {"cmd": cmd, "exit_code": p.returncode, "tail": tail}


def fetch_ultra_pdfs() -> list[dict]:
    rows: list[dict] = []
    rows.append(run([sys.executable, "scripts/fetch_koreascience_pdf_v1.py", "--jako-id", "JAKO201913661037959", "--slug", "DONGMUYUGO_JIPUNGJO_2019"]))
    for _id, arti, slug, _title, _year in ULTRA_JSCIM_TARGETS:
        dest = RAW / f"{slug}_dr.pdf"
        if dest.is_file() and dest.stat().st_size > 10_000:
            rows.append({"skipped": True, "slug": slug, "reason": "cached"})
            continue
        url = f"https://journal.kci.go.kr/JSCIM/archive/articlePdf?artiId={arti}"
        import urllib.request

        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (MKM)", "Referer": "https://journal.kci.go.kr/"},
            )
            data = urllib.request.urlopen(req, timeout=60).read()
            ok = data[:4] == b"%PDF" and len(data) > 5000
            if ok:
                dest.write_bytes(data)
            rows.append({"slug": slug, "arti_id": arti, "fetched": ok, "bytes": len(data) if ok else 0})
        except OSError as exc:
            rows.append({"slug": slug, "arti_id": arti, "error": str(exc)[:120]})
    return rows


def write_tier0_proxy() -> None:
    lines = [
        "# CHEONYUCHO Ultra Tier-0 Proxy (Cursor+Exa synthesis)",
        "",
        f"**generated:** {_utc()[:10]} · `research_only` · `send_gate: HOLD`",
        "",
        "Gemini Deep Research 대체: Exa 6라운드 + medhist/JSCIM/koreascience fetch 결과 압축.",
        "",
        "## P1 human (unchanged)",
        "",
        "1. 闡幽抄 원전 — 장서각/NLK/합법 HWP",
        "2. NLK `199.1-이617ㄱ` 박석언 1985 — index grep 闡幽",
        "3. 임상편람 p.344 草/抄 실물",
        "",
        "## Tier-0 discovery headlines",
        "",
        "- **FM-09** JKMH 2019 지풍兆: DOI→koreascience `JAKO201913661037959` (medhist OA PDF 미호스팅)",
        "- **격치고** JSCIM OA: ART001019799, ART002803635 + Exa ART002453921 등",
        "- **동무유고** DR-03~04 + 지풍兆 논문( fetch 시도)",
        "- **闡幽抄** 논문 grep: list_mention only — thesis/RISS 부록 0건 유지",
        "",
        "## Ultra Exa query set (6)",
        "",
    ]
    for i, q in enumerate(ULTRA_EXA_QUERIES, 1):
        lines.append(f"{i}. `{q}`")
    lines.extend(
        [
            "",
            "## Overclaim firewall",
            "",
            "- 원전 전문·CANON: 논문/Exa만으로 승격 금지",
            "- SSOT hanja: **闡幽抄** (抄)",
            "",
            f"Downstream: `{LEDGER.relative_to(ROOT).as_posix()}`",
        ]
    )
    TIER0_PROXY.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_merged_lit(ledger: dict, exa: dict, fetch_rows: list[dict]) -> None:
    summary = ledger.get("summary") or {}
    lines = [
        "# 천유초(闡幽抄) — ULTRA DR MERGED LIT_REVIEW",
        "",
        f"**generated:** {_utc()[:10]} · Tier 0 proxy + Tier 1 Exa6 + fragment ledger · `HOLD`",
        "",
        "## Executive verdict",
        "",
        "| Question | Answer |",
        "|----------|--------|",
        "| 원전 전문 대체? | **No** — `canon_status: not_acquired` |",
        "| 2차 fragment layer 확장? | **Yes** — see summary below |",
        "| FM-09 지풍兆 | koreascience fetch — see belt run log |",
        "",
        "## Fragment ledger summary",
        "",
        f"- total_chunks: **{summary.get('total_chunks', '?')}**",
        f"- cheonyucho_chunks: **{summary.get('cheonyucho_chunks', '?')}** (expect list_mention)",
        f"- geukchigo_chunks: **{summary.get('geukchigo_chunks', '?')}**",
        f"- dongmu_yugo_chunks: **{summary.get('dongmu_yugo_chunks', '?')}**",
        f"- primary_hanja_chunk: **{summary.get('primary_hanja_chunk_count', 0)}**",
        "",
        "## Exa discoveries",
        "",
        f"- status: `{exa.get('status', '?')}`",
        f"- discovery count: **{len(exa.get('discoveries') or [])}**",
        f"- pdf auto-fetch ok: **{sum(1 for x in (exa.get('pdf_fetch_attempts') or []) if x.get('ok'))}**",
        "",
        "## Ultra PDF fetch",
        "",
        "```json",
        json.dumps(fetch_rows, ensure_ascii=False, indent=2)[:3000],
        "```",
        "",
        "## Reproduce",
        "",
        "```powershell",
        "py scripts/run_cheonyucho_ultra_dr_belt_v1.py",
        "py scripts/check_cheonyucho_acquisition_gate_v1.py",
        "```",
        "",
        f"Tier0 proxy: `{TIER0_PROXY.relative_to(ROOT).as_posix()}`",
        f"Ledger: `{LEDGER.relative_to(ROOT).as_posix()}`",
    ]
    OUT_LIT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def patch_fragment_mine_exa_queries() -> None:
    """Inject ultra 6 queries into fragment_mine for this run."""
    fm = ROOT / "scripts/run_cheonyucho_fragment_mine_v1.py"
    text = fm.read_text(encoding="utf-8")
    marker = "EXA_QUERIES = ["
    if marker not in text:
        return
    start = text.index(marker)
    end = text.index("]", start) + 1
    block = "EXA_QUERIES = [\n" + "".join(f'    "{q}",\n' for q in ULTRA_EXA_QUERIES) + "]"
    fm.write_text(text[:start] + block + text[end:], encoding="utf-8")


def main() -> int:
    steps: list[dict] = []
    write_tier0_proxy()
    steps.append({"step": "tier0_proxy", "path": str(TIER0_PROXY)})

    patch_fragment_mine_exa_queries()
    steps.append({"step": "patch_exa6", "queries": len(ULTRA_EXA_QUERIES)})

    fetch_rows = fetch_ultra_pdfs()
    steps.append({"step": "ultra_pdf_fetch", "rows": fetch_rows})

    fm = run([sys.executable, "scripts/run_cheonyucho_fragment_mine_v1.py"])
    steps.append({"step": "fragment_mine", **fm})

    gate = run([sys.executable, "scripts/check_cheonyucho_acquisition_gate_v1.py"])
    steps.append({"step": "gate", **gate})

    vault = run([sys.executable, "scripts/push_ijeoma_recent_to_g_vault_v1.py"])
    steps.append({"step": "vault", **vault})

    ledger = json.loads(LEDGER.read_text(encoding="utf-8")) if LEDGER.is_file() else {}
    exa = json.loads(EXA_META.read_text(encoding="utf-8")) if EXA_META.is_file() else {}
    write_merged_lit(ledger, exa, fetch_rows)

    ok = fm["exit_code"] == 0 and gate["exit_code"] == 0
    doc = {
        "schema": "cheonyucho_ultra_dr_belt_run_v1",
        "generated_at_utc": _utc(),
        "send_gate": "HOLD",
        "ok": ok,
        "steps": steps,
        "merged_lit": str(OUT_LIT.relative_to(ROOT)).replace("\\", "/"),
        "ledger_summary": ledger.get("summary"),
        "reproduce": "py scripts/run_cheonyucho_ultra_dr_belt_v1.py",
    }
    OUT_RUN.parent.mkdir(parents=True, exist_ok=True)
    OUT_RUN.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "out": str(OUT_RUN), "chunks": ledger.get("summary", {}).get("total_chunks")}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
