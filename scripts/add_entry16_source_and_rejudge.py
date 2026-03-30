#!/usr/bin/env python3
"""Append one ENTRY_16 source row and regenerate gate artifacts."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "docs" / "final" / "artifacts" / "entry16_source_hunt_log.jsonl"
SUMMARY_SCRIPT = ROOT / "scripts" / "report_entry16_source_hunt.py"
GATE_SCRIPT = ROOT / "scripts" / "evaluate_entry16_promotion_gate.py"

ALLOWED_WITNESS = {"yes", "no", "unknown"}
ALLOWED_CONF = {"high", "med", "low"}
ALLOWED_ACCESS = {"public", "login", "institutional", "paywalled"}


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s:
            rows.append(json.loads(s))
    return rows


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Add ENTRY_16 source row and rejudge promotion gate.")
    p.add_argument("--source-url", required=True)
    p.add_argument("--source-title", required=True)
    p.add_argument("--publisher-or-host", required=True)
    p.add_argument("--resource-type", required=True)
    p.add_argument("--djd-volume", required=True)
    p.add_argument("--page-range", required=True)
    p.add_argument("--fragment-sigla", required=True)
    p.add_argument("--line-anchor", required=True)
    p.add_argument("--extant-verses-claim", required=True)
    p.add_argument("--witness", required=True, choices=sorted(ALLOWED_WITNESS))
    p.add_argument("--evidence-quote", required=True)
    p.add_argument("--confidence", required=True, choices=sorted(ALLOWED_CONF))
    p.add_argument("--access-mode", required=True, choices=sorted(ALLOWED_ACCESS))
    p.add_argument("--last-checked-utc", default="")
    p.add_argument("--dry-run", action="store_true")
    return p


def main() -> int:
    args = _build_parser().parse_args()
    rows = _rows(LOG)
    urls = {str(r.get("source_url", "")).strip() for r in rows}
    if args.source_url.strip() in urls:
        raise SystemExit(f"duplicate source_url: {args.source_url}")

    row = {
        "source_url": args.source_url.strip(),
        "source_title": args.source_title.strip(),
        "publisher_or_host": args.publisher_or_host.strip(),
        "resource_type": args.resource_type.strip(),
        "manuscript_id": "4Q117",
        "djd_volume": args.djd_volume.strip(),
        "page_range": args.page_range.strip(),
        "fragment_sigla": args.fragment_sigla.strip(),
        "line_anchor": args.line_anchor.strip(),
        "extant_verses_claim": args.extant_verses_claim.strip(),
        "ezra_2_54_direct_witness": args.witness.strip(),
        "evidence_quote": args.evidence_quote.strip(),
        "confidence": args.confidence.strip(),
        "access_mode": args.access_mode.strip(),
        "last_checked_utc": (args.last_checked_utc.strip() or _iso_now()),
    }
    if args.dry_run:
        print(json.dumps(row, ensure_ascii=False, indent=2))
        print("DRY-RUN: no file updates")
        return 0

    with LOG.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")

    # Rebuild summary and gate artifacts after source ingestion.
    subprocess.run([sys.executable, str(SUMMARY_SCRIPT)], check=True, cwd=str(ROOT))
    subprocess.run([sys.executable, str(GATE_SCRIPT)], check=True, cwd=str(ROOT))
    print("OK: row appended + summary/gate regenerated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
