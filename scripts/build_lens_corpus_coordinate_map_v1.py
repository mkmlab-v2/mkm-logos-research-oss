#!/usr/bin/env python3
"""Build lens corpus coordinate map from paper digest Tier0 files (B-track)."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.extract_lens_coordinate_facts_v1 import LENS_SCHEMA_MAP, extract_coordinate_facts

RAW = ROOT / "docs/research/raw"
ARTIFACTS = ROOT / "docs/final/artifacts"

LENS_OUT = {
    "ijeoma": ARTIFACTS / "ijeoma_corpus_coordinate_map_v1_latest.json",
    "logos": ARTIFACTS / "logos_corpus_coordinate_map_v1_latest.json",
    "myeongri": ARTIFACTS / "myeongri_corpus_coordinate_map_v1_latest.json",
}

# Legacy ijeoma cluster keys when schema has no cluster field
IJOEOMA_CLUSTER_FALLBACK = {
    "four_constitution_axis": "four_constitution",
    "philosophy_axis": "philosophy",
    "clinical_axis": "clinical",
    "comparison_axis": "comparison",
    "primary_corpus_cited": "corpus_primary",
}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _extract_excerpt_from_tier0(md_text: str) -> str:
    m = re.search(r"## Full text excerpt\s*\n\s*```\s*\n(.*?)```", md_text, re.DOTALL)
    if m:
        return m.group(1).strip()
    return md_text


def _load_schema_fields(lens: str) -> dict[str, str]:
    schema_path = LENS_SCHEMA_MAP.get(lens)
    if not schema_path or not schema_path.is_file():
        return {}
    doc = json.loads(schema_path.read_text(encoding="utf-8"))
    mapping: dict[str, str] = {}
    for field in doc.get("fields") or []:
        fid = str(field.get("field_id") or "")
        if not fid:
            continue
        cluster = field.get("cluster") or IJOEOMA_CLUSTER_FALLBACK.get(fid) or fid
        mapping[fid] = str(cluster)
    return mapping


def build_coordinate_map(*, lens: str) -> dict[str, Any]:
    glob_lens = lens if lens != "logos" else "logos"
    tier0_files = sorted(RAW.glob(f"{glob_lens}_*_PAPER_DIGEST_tier0_v1.md"))
    field_clusters = _load_schema_fields(lens)
    papers: list[dict[str, Any]] = []
    field_totals: dict[str, float] = {}
    clusters: dict[str, list[str]] = {}

    for path in tier0_files:
        md = path.read_text(encoding="utf-8", errors="replace")
        text = _extract_excerpt_from_tier0(md)
        title_m = re.search(r"^#\s+Tier 0 — Paper digest ·\s*(.+)$", md, re.M)
        title = title_m.group(1).strip() if title_m else path.stem
        facts = extract_coordinate_facts(text, lens=lens, title=title)
        by_field = {str(f["field_id"]): int(f["value"]) for f in facts}
        for fid, val in by_field.items():
            field_totals[fid] = field_totals.get(fid, 0.0) + val
            cluster_key = field_clusters.get(fid, "other")
            clusters.setdefault(cluster_key, [])
            tier_key = path.relative_to(ROOT).as_posix()
            if tier_key not in clusters[cluster_key]:
                clusters[cluster_key].append(tier_key)
        papers.append(
            {
                "tier0": path.relative_to(ROOT).as_posix(),
                "title_guess": title[:160],
                "coordinate_hits": by_field,
                "fact_count": len(facts),
            }
        )

    no_hits = [p["tier0"] for p in papers if not p["coordinate_hits"]]
    if no_hits:
        clusters["other"] = no_hits

    return {
        "schema": "lens_corpus_coordinate_map_v1",
        "generated_at_utc": _utc(),
        "send_gate": "HOLD",
        "research_only": True,
        "lens": lens,
        "paper_count": len(papers),
        "field_totals": field_totals,
        "clusters": {k: v for k, v in clusters.items() if v},
        "papers": papers,
        "reproduce": f"py scripts/build_lens_corpus_coordinate_map_v1.py --lens {lens}",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lens", choices=sorted(LENS_SCHEMA_MAP.keys()), required=True)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    out = args.out or LENS_OUT.get(args.lens) or ARTIFACTS / f"{args.lens}_corpus_coordinate_map_v1_latest.json"
    doc = build_coordinate_map(lens=args.lens)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "lens": args.lens, "paper_count": doc["paper_count"], "out": str(out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
