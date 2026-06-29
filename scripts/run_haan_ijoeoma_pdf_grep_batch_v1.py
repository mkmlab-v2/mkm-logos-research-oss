#!/usr/bin/env python3
"""Batch grep haan library ijeoma PDFs for 천유초 / 闡幽 signals."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "data/corpus/ijeoma/secondary/library_capture/2026-06-28"
OUT = ROOT / "reports/constitution/btrack_pilot/haan_ijoeoma_pdf_grep_batch_v1_latest.json"
GREP = ROOT / "scripts/grep_cheonyucho_pdf_v1.py"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    pdfs = sorted(CORPUS.rglob("*.pdf"))
    rows: list[dict] = []
    for pdf in pdfs:
        rel = pdf.relative_to(ROOT).as_posix()
        out_json = ROOT / "reports/constitution/btrack_pilot/grep" / f"{pdf.stem[:80]}_grep_cheonyucho_v1.json"
        r = subprocess.run(
            [sys.executable, str(GREP), "--pdf", str(pdf), "--out", str(out_json)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        row: dict = {"pdf": rel, "exit_code": r.returncode}
        if out_json.is_file():
            doc = json.loads(out_json.read_text(encoding="utf-8"))
            row.update(
                {
                    "verdict": doc.get("verdict"),
                    "cheonyucho_in_pdf": doc.get("cheonyucho_in_pdf"),
                    "terms": list((doc.get("term_hits") or {}).keys()),
                    "grep_out": out_json.relative_to(ROOT).as_posix(),
                }
            )
        else:
            row["error"] = (r.stderr or r.stdout)[-300:]
        rows.append(row)

    hits = [x for x in rows if x.get("cheonyucho_in_pdf")]
    doc = {
        "schema": "haan_ijoeoma_pdf_grep_batch_v1",
        "generated_at_utc": _utc(),
        "send_gate": "HOLD",
        "pdf_count": len(rows),
        "cheonyucho_hit_count": len(hits),
        "cheonyucho_hits": hits,
        "all": rows,
        "reproduce": "py scripts/run_haan_ijoeoma_pdf_grep_batch_v1.py",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"ok": True, "pdf_count": len(rows), "cheonyucho_hits": len(hits), "out": str(OUT)},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
