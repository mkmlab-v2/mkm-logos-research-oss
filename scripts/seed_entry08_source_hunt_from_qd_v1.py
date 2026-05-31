#!/usr/bin/env python3
"""Seed ENTRY_08 (4Q319) source-hunt log with QD/IAA/DJD probes [HYPO]."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "docs" / "final" / "artifacts" / "entry08_source_hunt_log.jsonl"
PROBE = ROOT / "reports" / "qd_transcription_probe_latest.json"
REPORT_SCRIPT = ROOT / "scripts" / "report_entry08_source_hunt_v1.py"
UA = "MKM-research/1.0 (seed_entry08_source_hunt_from_qd_v1)"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _probe(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            body = resp.read(80_000).decode("utf-8", errors="replace")
            return {
                "http_status": resp.status,
                "ok": True,
                "has_hebrew": bool(__import__("re").search(r"[\u0590-\u05FF]", body)),
                "has_line_table_hint": "line" in body.lower() and ("<tr" in body or "|" in body),
                "title": _title(body),
            }
    except urllib.error.HTTPError as e:
        return {"http_status": e.code, "ok": False, "error": str(e)}
    except Exception as e:  # noqa: BLE001
        return {"http_status": None, "ok": False, "error": str(e)}


def _title(html: str) -> str:
    import re

    m = re.search(r"<title[^>]*>([^<]+)</title>", html, re.I)
    return (m.group(1).strip()[:100] if m else "")


def _existing_urls(path: Path) -> set[str]:
    if not path.exists():
        return set()
    out: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s:
            out.add(str(json.loads(s).get("source_url", "")).strip())
    return out


def _append(row: dict, urls: set[str], buf: list[str]) -> None:
    u = str(row.get("source_url", "")).strip()
    if u in urls:
        return
    buf.append(json.dumps(row, ensure_ascii=False))
    urls.add(u)


def main() -> int:
    urls = _existing_urls(LOG)
    new_rows: list[str] = []
    now = _iso_now()

    qd_candidates = [
        "https://lexicon.qumran-digital.org/transcriptions/4Q319/",
        "https://lexicon.qumran-digital.org/transcriptions/4Q319/2025-11-11/index.html",
        "https://lexicon.qumran-digital.org/transcriptions/4Q319/2024-07-30/index.html",
        "https://lexicon.qumran-digital.org/transcriptions/4QOtot/",
    ]
    for url in qd_candidates:
        pr = _probe(url)
        witness = "no"
        if pr.get("ok") and pr.get("has_line_table_hint"):
            witness = "unknown"
        _append(
            {
                "source_url": url,
                "source_title": f"4Q319 QD probe ({pr.get('http_status')})",
                "publisher_or_host": "Qumran-Digital",
                "resource_type": "availability_probe",
                "manuscript_id": "4Q319",
                "djd_volume": "DJD XXI",
                "page_range": "Pls X-XIII (catalog)",
                "fragment_sigla": "4QOtot",
                "line_anchor": "probe only",
                "extant_claim": json.dumps(pr, ensure_ascii=False)[:400],
                "fragment_line_direct_witness": witness,
                "evidence_quote": f"HTTP probe: ok={pr.get('ok')} hebrew={pr.get('has_hebrew')}",
                "confidence": "high",
                "access_mode": "public",
                "last_checked_utc": now,
                "artifact_ref": "scripts/seed_entry08_source_hunt_from_qd_v1.py",
            },
            urls,
            new_rows,
        )

    static_rows = [
        {
            "source_url": "https://www.deadseascrolls.org.il/explore-the-archive/manuscript/4Q319-1?locale=en_US",
            "source_title": "The Dead Sea Scrolls - 4Q Otot",
            "publisher_or_host": "Israel Antiquities Authority",
            "resource_type": "archive_images_metadata",
            "manuscript_id": "4Q319",
            "djd_volume": "DJD XXI",
            "page_range": "194-244 (DJD XXI 4QOtot)",
            "fragment_sigla": "4QOtot",
            "line_anchor": "plate=Pls X-XIII line=TBD (no public line transcription on page)",
            "extant_claim": "Manuscript images/catalog; line table not exported on public archive",
            "fragment_line_direct_witness": "no",
            "evidence_quote": "CHECKLIST 2026-03-30: IAA page confirms manuscript, not line-level transcription",
            "confidence": "med",
            "access_mode": "public",
            "last_checked_utc": now,
            "artifact_ref": "docs/final/CROSS_REF_CITATION_ANCHOR_EVIDENCE_CHECKLIST_2026-03-30.md",
        },
        {
            "source_url": "https://www.persee.fr/doc/rhpr_0035-2403_2009_num_89_1_1373",
            "source_title": "4Q319 Otot — annotated translation (Persée)",
            "publisher_or_host": "Persée / Revue d'histoire et de philosophie religieuses",
            "resource_type": "scholarly_translation",
            "manuscript_id": "4Q319",
            "djd_volume": "DJD XXI (primary edition)",
            "page_range": "unknown",
            "fragment_sigla": "4QOtot",
            "line_anchor": "translation line numbers (not DJD fragment-line sigla)",
            "extant_claim": "French translation with line-style numbering; not machine fragment-line anchor",
            "fragment_line_direct_witness": "no",
            "evidence_quote": "Scholarly translation layer — use for thematic cross-check only, not verified_anchor",
            "confidence": "med",
            "access_mode": "public",
            "last_checked_utc": now,
            "artifact_ref": "docs/final/artifacts/CROSS_REF_DSS_TO_STATES_DRAFT.json ENTRY_08",
        },
        {
            "source_url": "djd-local://talmon-2001-djd-xxi-4qotot-pls-x-xiii",
            "source_title": "DJD XXI Calendrical Texts (4QOtot)",
            "publisher_or_host": "Oxford/Clarendon (DJD)",
            "resource_type": "primary_print_edition",
            "manuscript_id": "4Q319",
            "djd_volume": "DJD XXI",
            "page_range": "Pls X-XIII",
            "fragment_sigla": "4QOtot",
            "line_anchor": "institutional access required",
            "extant_claim": "Plate/sigla confirmed in SSOT; fragment-line in licensed edition",
            "fragment_line_direct_witness": "unknown",
            "evidence_quote": "CHECKLIST: public line transcription unavailable; DJD XXI is primary for plates",
            "confidence": "high",
            "access_mode": "institutional",
            "last_checked_utc": now,
            "artifact_ref": "docs/final/btrack_dss_4Q319_otot.md",
        },
        {
            "source_url": "https://lexicon.qumran-digital.org/transcriptions/4Q169/2025-03-11/index.html",
            "source_title": "4Q169 (contrast) — QD has line transcription",
            "publisher_or_host": "Qumran-Digital",
            "resource_type": "transcription_line_anchor",
            "manuscript_id": "4Q169",
            "djd_volume": "DJD V",
            "page_range": "n/a",
            "fragment_sigla": "4Q169 frags 3-4 col.ii",
            "line_anchor": "ENTRY_09 reference: frags 3-4 col.ii lines 1-12 (not ENTRY_08)",
            "extant_claim": "Positive control: QD line transcriptions exist for other MSS, not 4Q319",
            "fragment_line_direct_witness": "no",
            "evidence_quote": "Shows QD line capability; does not satisfy 4Q319 ENTRY_08",
            "confidence": "high",
            "access_mode": "public",
            "last_checked_utc": now,
            "artifact_ref": "docs/final/artifacts/CROSS_REF_DSS_TO_STATES_DRAFT.json ENTRY_09",
        },
    ]
    for row in static_rows:
        _append(row, urls, new_rows)

    if PROBE.exists():
        pr = json.loads(PROBE.read_text(encoding="utf-8"))
        block = next((b for b in pr.get("results", []) if b.get("manuscript_id") == "4Q319"), None)
        if block:
            _append(
                {
                    "source_url": "artifact://reports/qd_transcription_probe_latest.json#4Q319",
                    "source_title": "QD probe aggregate ENTRY_08",
                    "publisher_or_host": "MKM",
                    "resource_type": "availability_probe",
                    "manuscript_id": "4Q319",
                    "djd_volume": "DJD XXI",
                    "page_range": "unknown",
                    "fragment_sigla": "4QOtot",
                    "line_anchor": "probe only",
                    "extant_claim": json.dumps(block, ensure_ascii=False)[:500],
                    "fragment_line_direct_witness": "no",
                    "evidence_quote": "best_ok=false on 4Q319 QD URLs (403/404)",
                    "confidence": "high",
                    "access_mode": "public",
                    "last_checked_utc": pr.get("generated_at_utc", now),
                    "artifact_ref": "reports/qd_transcription_probe_latest.json",
                },
                urls,
                new_rows,
            )

    if new_rows:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a", encoding="utf-8", newline="\n") as f:
            for line in new_rows:
                f.write(line + "\n")
        print(f"APPENDED: {len(new_rows)} rows -> {LOG}")
    elif not LOG.exists():
        LOG.write_text("", encoding="utf-8")
        print(f"CREATED empty log (no rows?) -> {LOG}")
    else:
        print("SKIP: no new rows")

    import subprocess

    subprocess.run([sys.executable, str(REPORT_SCRIPT)], check=True, cwd=str(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
