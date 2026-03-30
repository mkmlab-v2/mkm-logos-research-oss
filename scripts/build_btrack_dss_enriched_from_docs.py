#!/usr/bin/env python3
"""Build enriched DSS JSONL from local/shared DSS markdown docs."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT / "docs" / "final"
SHARED_VAULT_DIR = Path(r"G:\공유 드라이브\MKM_DATA_VAULT\vault")
OUT = ROOT / "data" / "logos" / "manuscripts" / "dss_parsed_enriched.jsonl"
DEFAULT_GLOBS = (
    "btrack_dss*.md",
    "DSS_APOCRYPHA_FRONTLINE_CLOSEOUT_*.md",
    "NOTEBOOKLM_DSS_APOCRYPHA_BUNDLE_NOTE*.md",
    "CROSS_REF_CITATION_ANCHOR_EVIDENCE_CHECKLIST_*.md",
)
EVIDENCE_RE = re.compile(r"\b(1Q|4Q|11Q|Qumran|DSS|Dead Sea Scrolls|War Scroll|Community Rule)\b", re.I)


def _sentences(text: str) -> list[str]:
    text = re.sub(r"`[^`]+`", " ", text)
    text = re.sub(r"\[[^\]]+\]\([^)]+\)", " ", text)
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"[>#*-]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    parts = re.split(r"(?<=[.!?])\s+|(?<=\.)\s+(?=[A-Z])", text)
    out: list[str] = []
    for p in parts:
        s = p.strip(" -\t\r\n")
        if len(s) < 40:
            continue
        out.append(s)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Build enriched DSS parsed jsonl from local docs")
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument(
        "--glob",
        default=",".join(DEFAULT_GLOBS),
        help="Comma-separated glob patterns under docs/final for DSS markdown inputs",
    )
    ap.add_argument(
        "--include-shared-vault",
        action="store_true",
        help="Also search shared vault path for matching markdown docs.",
    )
    ap.add_argument(
        "--shared-vault-dir",
        default=str(SHARED_VAULT_DIR),
        help="Shared vault root path used when --include-shared-vault is set.",
    )
    ap.add_argument("--min-len", type=int, default=30, help="Minimum sentence length to keep")
    ap.add_argument(
        "--require-evidence-keyword",
        action="store_true",
        help="Keep only sentences that contain DSS evidence keywords (recommended).",
    )
    args = ap.parse_args()

    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = ROOT / out_path

    patterns = [p.strip() for p in str(args.glob).split(",") if p.strip()]
    docs_set: set[Path] = set()
    for pat in patterns:
        for p in DOCS_DIR.glob(pat):
            if p.is_file():
                docs_set.add(p)
    shared_docs_count = 0
    if args.include_shared_vault:
        shared_root = Path(args.shared_vault_dir)
        if shared_root.is_dir():
            for pat in patterns:
                for p in shared_root.rglob(pat):
                    if p.is_file():
                        docs_set.add(p)
                        shared_docs_count += 1
    docs = sorted(docs_set)
    rows: list[dict[str, object]] = []
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rid = 1
    seen: dict[str, int] = {}
    provenance_by_norm: dict[str, set[str]] = {}
    for doc in docs:
        if not doc.is_file():
            continue
        raw = doc.read_text(encoding="utf-8")
        for s in _sentences(raw):
            if len(s) < args.min_len:
                continue
            if args.require_evidence_keyword and not EVIDENCE_RE.search(s):
                continue
            norm = s.lower().strip()
            try:
                source_doc = str(doc.relative_to(ROOT))
            except ValueError:
                source_doc = str(doc)
            if norm in seen:
                provenance_by_norm.setdefault(norm, set()).add(source_doc)
                continue
            provenance_by_norm[norm] = {source_doc}
            rows.append(
                {
                    "id": f"dss_enriched_{rid:04d}",
                    "source": "dss",
                    "source_doc": source_doc,
                    "source_docs": [source_doc],
                    "has_shared_source": source_doc.startswith(str(SHARED_VAULT_DIR)),
                    "text": s,
                    "ingested_at_utc": ts,
                }
            )
            seen[norm] = len(rows) - 1
            rid += 1

    # Attach merged provenance for deduplicated sentences.
    for norm, idx in seen.items():
        docs_sorted = sorted(provenance_by_norm.get(norm, set()))
        rows[idx]["source_docs"] = docs_sorted
        rows[idx]["has_shared_source"] = any(x.startswith(str(SHARED_VAULT_DIR)) for x in docs_sorted)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print("OK: dss enriched jsonl built")
    print(f"out={out_path}")
    print(f"docs={len(docs)}")
    if args.include_shared_vault:
        print(f"shared_docs_scanned={shared_docs_count}")
    print(f"rows={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
