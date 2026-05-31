#!/usr/bin/env python3
"""Probe Qumran-Digital transcription URL availability for CROSS_REF ENTRY_07/08 [HYPO]."""

from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "qd_transcription_probe_latest.json"

UA = "MKM-research/1.0 (probe_qumran_digital_transcription_availability_v1)"

TARGETS = [
    {
        "manuscript_id": "11Q19",
        "entry": "ENTRY_07",
        "urls": [
            "https://lexicon.qumran-digital.org/transcriptions/11Q19/",
            "https://lexicon.qumran-digital.org/transcriptions/11Q19/2025-11-11/index.html",
        ],
    },
    {
        "manuscript_id": "11Q20",
        "entry": "ENTRY_07_comparandum",
        "urls": [
            "https://lexicon.qumran-digital.org/transcriptions/11Q20/",
            "https://lexicon.qumran-digital.org/transcriptions/11Q20/2025-11-11/index.html",
        ],
    },
    {
        "manuscript_id": "4Q319",
        "entry": "ENTRY_08",
        "urls": [
            "https://lexicon.qumran-digital.org/transcriptions/4Q319/",
            "https://lexicon.qumran-digital.org/transcriptions/4QOtot/",
        ],
    },
]

LINE_ROW_RE = re.compile(r"^\|\s*\d+\s*\|", re.MULTILINE)


def probe_url(url: str, timeout: int = 45) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read(200_000).decode("utf-8", errors="replace")
            line_rows = len(LINE_ROW_RE.findall(body))
            return {
                "url": url,
                "http_status": resp.status,
                "ok": True,
                "content_type": resp.headers.get("Content-Type", ""),
                "body_bytes_sampled": len(body.encode("utf-8", errors="ignore")),
                "line_table_rows_sampled": line_rows,
                "title_snippet": _title_snippet(body),
            }
    except urllib.error.HTTPError as e:
        return {"url": url, "http_status": e.code, "ok": False, "error": str(e)}
    except Exception as e:  # noqa: BLE001 — probe must not crash
        return {"url": url, "http_status": None, "ok": False, "error": str(e)}


def _title_snippet(html: str) -> str:
    m = re.search(r"<title[^>]*>([^<]+)</title>", html, re.I)
    return (m.group(1).strip()[:120] if m else "")


def main() -> int:
    results = []
    for block in TARGETS:
        url_results = [probe_url(u) for u in block["urls"]]
        best = next((r for r in url_results if r.get("ok")), None)
        results.append(
            {
                "manuscript_id": block["manuscript_id"],
                "entry": block["entry"],
                "urls": url_results,
                "best_ok": best is not None,
                "line_table_rows_on_best": (best or {}).get("line_table_rows_sampled", 0),
            }
        )

    payload = {
        "schema": "qd_transcription_probe_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "track": "B-track",
        "research_only": True,
        "hypo": True,
        "note": "Availability probe only; does not update CROSS_REF_DSS_TO_STATES_DRAFT.json.",
        "results": results,
        "operator_hint": (
            "11Q20 line transcription may support comparandum mapping to 11Q19 cols XLVI-XLVII; "
            "manual column crosswalk required. 4Q319 may need alternate siglum URLs or DJD."
        ),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(OUT), "results": results}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
