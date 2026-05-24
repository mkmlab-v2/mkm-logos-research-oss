#!/usr/bin/env python3
"""Harvest logos verse_decoded_v2.jsonl into Golden 40 homogeneous expansion lane (B-track)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = ROOT / "docs/final/artifacts/golden_40_logos_verse_lane_manifest_v1.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/golden_40_logos_verse_compression_lane_v1.json"


def _shorten_words(text: str, ratio: float = 0.55) -> str:
    words = text.split()
    if not words:
        return text
    keep = max(1, int(len(words) * ratio))
    return " ".join(words[:keep])


def _verse_raw(row: dict[str, Any]) -> str:
    ref = str(row.get("source_ref") or row.get("verse_id") or "").strip()
    edition = str(row.get("edition") or "").strip()
    text = str(row.get("text") or row.get("original_text") or "").strip()
    interp = str(row.get("interpretation") or "").strip()
    head = f"{ref} ({edition}): {text}" if edition else f"{ref}: {text}"
    if interp and len(interp) < 120:
        return f"{head}. [{interp}]"
    return head


def _harvest(
    jsonl_path: Path,
    *,
    max_cases: int,
    min_chars: int,
    stride: int,
) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    idx = 1
    line_no = 0
    with jsonl_path.open(encoding="utf-8") as fh:
        for line in fh:
            line_no += 1
            if stride > 1 and (line_no - 1) % stride != 0:
                continue
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            raw = _verse_raw(row)
            if len(raw) < min_chars:
                continue
            comp = _shorten_words(raw, 0.55)
            cases.append(
                {
                    "id": f"logos_v_{idx:04d}",
                    "raw_text": raw,
                    "compressed_text": comp,
                    "reconstructed_text": comp,
                    "domain": "logos_verse_ancient",
                    "source_verse_id": row.get("verse_id"),
                    "source_edition": row.get("edition"),
                    "source_line": line_no,
                }
            )
            idx += 1
            if len(cases) >= max_cases:
                break
    return cases


def main() -> int:
    ap = argparse.ArgumentParser(description="Build logos verse homogeneous expansion lane.")
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    manifest_path = args.manifest if args.manifest.is_absolute() else ROOT / args.manifest
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    jsonl_rel = str(manifest.get("source_jsonl") or "data/logos/verse_decoded_v2.jsonl")
    jsonl_path = ROOT / jsonl_rel
    if not jsonl_path.is_file():
        print(f"error: missing jsonl: {jsonl_path}", file=sys.stderr)
        return 2

    max_cases = int(manifest.get("max_cases") or 360)
    min_chars = int(manifest.get("min_text_chars") or 24)
    stride = int(manifest.get("stride") or 80)
    cases = _harvest(jsonl_path, max_cases=max_cases, min_chars=min_chars, stride=stride)

    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_doc = {
        "schema": "multilens_performance_eval_input_v1",
        "description": "Golden 40 homogeneous logos verse lane from verse_decoded_v2.jsonl stride sample.",
        "research_only": True,
        "boundary_ack": manifest.get("boundary_ack"),
        "lane_id": manifest.get("lane_id"),
        "domain_tag": manifest.get("domain_tag"),
        "source_manifest": str(manifest_path.relative_to(ROOT)).replace("\\", "/"),
        "source_jsonl": jsonl_rel,
        "stride": stride,
        "compression_cases": cases,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(out_path), "case_count": len(cases)}, ensure_ascii=False))
    return 0 if cases else 1


if __name__ == "__main__":
    raise SystemExit(main())
