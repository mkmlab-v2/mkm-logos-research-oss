#!/usr/bin/env python3
"""Export Logos OL bridge deck + SSOT MD to PDF (headless Edge/Chrome · internal)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DECK_MD = ROOT / "reports/logos_ops_deck/logos_ol_bridge_deck_v1.md"
BRIDGE_MD = ROOT / "docs/final/LOGOS_ORIGINAL_LANGUAGE_GRAPH_RAG_BRIDGE_V1.md"
EVIDENCE_MD = ROOT / "docs/final/artifacts/logos_graphrag_bridge_evidence_pack_v1_latest.md"
OUT_DIR = ROOT / "reports/logos_ops_deck"
DEFAULT_MANIFEST = OUT_DIR / "logos_ol_bridge_deck_pdf_export_v1_latest.json"
MIN_PDF_BYTES = 2_000


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _export_one(*, source_md: Path, pdf_out: Path, title: str) -> dict[str, Any]:
    from export_opendata_327_submission_pdf_v1 import _export_part, _find_browser

    if not source_md.is_file():
        return {"source": str(source_md), "ok": False, "error": "missing source"}
    browser = _find_browser()
    html_out = pdf_out.with_suffix(".html")
    part = _export_part(
        browser=browser,
        source_md=source_md,
        html_out=html_out,
        pdf_out=pdf_out,
        title=title,
    )
    size = pdf_out.stat().st_size if pdf_out.is_file() else 0
    ok = size >= MIN_PDF_BYTES
    return {
        "ok": ok,
        "title": title,
        "source_md": part["source_md"],
        "html": part["html"],
        "pdf": part["pdf"],
        "size_kb": part["size_kb"],
        "min_bytes_ok": size >= MIN_PDF_BYTES,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--deck-md", type=Path, default=DECK_MD)
    ap.add_argument("--bridge-md", type=Path, default=BRIDGE_MD)
    ap.add_argument("--evidence-md", type=Path, default=EVIDENCE_MD)
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    ap.add_argument("--manifest-json", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--skip-bridge", action="store_true")
    ap.add_argument("--skip-evidence", action="store_true")
    args = ap.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    exports: list[dict[str, Any]] = []

    exports.append(
        _export_one(
            source_md=args.deck_md,
            pdf_out=args.out_dir / "logos_ol_bridge_deck_v1.pdf",
            title="Logos OL GraphRAG Bridge Deck v1",
        )
    )
    if not args.skip_bridge:
        exports.append(
            _export_one(
                source_md=args.bridge_md,
                pdf_out=args.out_dir / "logos_original_language_graph_rag_bridge_v1.pdf",
                title="Logos Original Language GraphRAG Bridge v1",
            )
        )
    if not args.skip_evidence and args.evidence_md.is_file():
        exports.append(
            _export_one(
                source_md=args.evidence_md,
                pdf_out=args.out_dir / "logos_graphrag_bridge_evidence_pack_v1.pdf",
                title="Logos GraphRAG Bridge Evidence Pack v1",
            )
        )

    ok = all(e.get("ok") for e in exports)
    manifest = {
        "schema": "logos_ol_bridge_deck_pdf_export_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "non_gating": True,
        "send_gate": "HOLD",
        "human_signoff_required": True,
        "ok": ok,
        "exports": exports,
        "reproduce": "py scripts/export_logos_ol_bridge_deck_pdf_v1.py",
    }
    args.manifest_json.parent.mkdir(parents=True, exist_ok=True)
    args.manifest_json.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "manifest": str(args.manifest_json)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
