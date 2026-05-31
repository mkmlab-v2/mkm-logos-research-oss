#!/usr/bin/env python3
"""Seed ENTRY_07 source-hunt log from QD probe/fetch artifacts (idempotent by source_url)."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "docs" / "final" / "artifacts" / "entry07_source_hunt_log.jsonl"
PROBE = ROOT / "reports" / "qd_transcription_probe_latest.json"
EXTRACT = ROOT / "reports" / "qd_11q20_transcription_extract_latest.json"
REPORT_SCRIPT = ROOT / "scripts" / "report_entry07_source_hunt_v1.py"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _existing_urls(path: Path) -> set[str]:
    if not path.exists():
        return set()
    urls: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s:
            continue
        row = json.loads(s)
        urls.add(str(row.get("source_url", "")).strip())
    return urls


def _append(row: dict, urls: set[str], out_lines: list[str]) -> None:
    u = str(row.get("source_url", "")).strip()
    if u in urls:
        return
    out_lines.append(json.dumps(row, ensure_ascii=False))
    urls.add(u)


def main() -> int:
    urls = _existing_urls(LOG)
    new_rows: list[str] = []
    now = _iso_now()

    static_rows = [
        {
            "source_url": "https://lexicon.qumran-digital.org/transcriptions/11Q19/2025-11-11/index.html",
            "source_title": "11Q19 (transcription) - Qumran-Digital",
            "publisher_or_host": "Qumran-Digital",
            "resource_type": "transcription_line_anchor",
            "manuscript_id": "11Q19",
            "djd_volume": "DJD XXIII (Temple comparanda)",
            "page_range": "unknown",
            "fragment_sigla": "11Q19 Temple Scroll",
            "line_anchor": "cols.XLVI-XLVII line=TBD",
            "extant_claim": "HTTP 404 on 2026-05-31 probe; no public line transcription",
            "xlvi_xlvii_direct_witness": "no",
            "comparandum_only": False,
            "evidence_quote": "probe_qumran_digital: 11Q19 URLs returned 404 Not Found",
            "confidence": "high",
            "access_mode": "public",
            "last_checked_utc": now,
            "artifact_ref": "reports/qd_transcription_probe_latest.json",
        },
        {
            "source_url": "http://dss.collections.imj.org.il/temple",
            "source_title": "Digital DSS - Temple Scroll (11Q19)",
            "publisher_or_host": "Israel Museum",
            "resource_type": "archive_images_metadata",
            "manuscript_id": "11Q19",
            "djd_volume": "Yadin 1977-1983",
            "page_range": "unknown",
            "fragment_sigla": "11Q19",
            "line_anchor": "cols.XLVI-XLVII line=TBD (images; no machine line table)",
            "extant_claim": "Scroll imagery and catalog; line-level transcription not exported",
            "xlvi_xlvii_direct_witness": "no",
            "comparandum_only": False,
            "evidence_quote": "IAA temple scroll page describes 66 columns; no downloadable line index for XLVI",
            "confidence": "med",
            "access_mode": "public",
            "last_checked_utc": now,
            "artifact_ref": "docs/final/CROSS_REF_CITATION_ANCHOR_EVIDENCE_CHECKLIST_2026-03-30.md",
        },
        {
            "source_url": "djd-local://yadin-1977-1983-11q19-cols-xlvi-xlvii",
            "source_title": "Yadin Temple Scroll edition (11Q19 cols XLVI-XLVII)",
            "publisher_or_host": "DJD/Yadin",
            "resource_type": "primary_print_edition",
            "manuscript_id": "11Q19",
            "djd_volume": "Yadin 1977-1983; DJD XXIII comparanda",
            "page_range": "cols XLVI-XLVII (print)",
            "fragment_sigla": "11Q19",
            "line_anchor": "institutional access required",
            "extant_claim": "Column-range cited in SSOT; line numbers in closed/licensed edition",
            "xlvi_xlvii_direct_witness": "unknown",
            "comparandum_only": False,
            "evidence_quote": "CHECKLIST: public line-level transcription unavailable; Yadin primary for column-range",
            "confidence": "high",
            "access_mode": "institutional",
            "last_checked_utc": now,
            "artifact_ref": "docs/final/artifacts/CROSS_REF_DSS_TO_STATES_DRAFT.json ENTRY_07",
        },
    ]
    for row in static_rows:
        _append(row, urls, new_rows)

    if EXTRACT.exists():
        ex = json.loads(EXTRACT.read_text(encoding="utf-8"))
        demo = ex.get("demo_fragment_column_lines") or {}
        demo_lines = demo.get("lines") or []
        sample = demo_lines[8:11] if len(demo_lines) > 10 else demo_lines[:3]
        line_bits = "; ".join(
            f"frag5 line {x.get('line')}: {x.get('text', '')[:40]}" for x in sample
        )
        _append(
            {
                "source_url": str(ex.get("source_url", "")).strip(),
                "source_title": "11Q20 (transcription) - Qumran-Digital",
                "publisher_or_host": "Qumran-Digital",
                "resource_type": "transcription_line_anchor",
                "manuscript_id": "11Q20",
                "djd_volume": "DJD XXIII (Temple b)",
                "page_range": "unknown",
                "fragment_sigla": f"QD fragment col {demo.get('qd_fragment_column')}",
                "line_anchor": line_bits or "fragment col 5 lines extracted",
                "extant_claim": (
                    f"QD page fragment cols {ex.get('qd_fragment_column_range')}; "
                    "NOT 11Q19 cols XLVI-XLVII"
                ),
                "xlvi_xlvii_direct_witness": "no",
                "comparandum_only": True,
                "evidence_quote": str(ex.get("entry_07_conclusion", ""))[:500],
                "confidence": "high",
                "access_mode": "public",
                "last_checked_utc": ex.get("generated_at_utc", now),
                "artifact_ref": "reports/qd_11q20_transcription_extract_latest.json",
            },
            urls,
            new_rows,
        )

    if PROBE.exists():
        pr = json.loads(PROBE.read_text(encoding="utf-8"))
        for block in pr.get("results", []):
            mid = block.get("manuscript_id", "")
            for u in block.get("urls", []):
                url = str(u.get("url", "")).strip()
                if not url:
                    continue
                _append(
                    {
                        "source_url": url,
                        "source_title": f"{mid} QD probe {u.get('http_status')}",
                        "publisher_or_host": "Qumran-Digital",
                        "resource_type": "availability_probe",
                        "manuscript_id": mid,
                        "djd_volume": "unknown",
                        "page_range": "unknown",
                        "fragment_sigla": mid,
                        "line_anchor": "probe only",
                        "extant_claim": str(u.get("error") or f"http {u.get('http_status')}"),
                        "xlvi_xlvii_direct_witness": "no",
                        "comparandum_only": mid == "11Q20",
                        "evidence_quote": f"entry={block.get('entry')} best_ok={block.get('best_ok')}",
                        "confidence": "high",
                        "access_mode": "public",
                        "last_checked_utc": pr.get("generated_at_utc", now),
                        "artifact_ref": "reports/qd_transcription_probe_latest.json",
                    },
                    urls,
                    new_rows,
                )

    if not new_rows and LOG.exists():
        print("SKIP: no new rows (all source_url already logged)")
    elif new_rows:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a", encoding="utf-8", newline="\n") as f:
            for line in new_rows:
                f.write(line + "\n")
        print(f"APPENDED: {len(new_rows)} rows -> {LOG}")
    else:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        for row in static_rows:
            new_rows.append(json.dumps(row, ensure_ascii=False))
        LOG.write_text("\n".join(new_rows) + "\n", encoding="utf-8")
        print(f"CREATED: {len(new_rows)} rows -> {LOG}")

    import subprocess

    subprocess.run([sys.executable, str(REPORT_SCRIPT)], check=True, cwd=str(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
