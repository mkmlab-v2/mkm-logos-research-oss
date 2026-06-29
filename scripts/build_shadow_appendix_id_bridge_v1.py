#!/usr/bin/env python3
"""Unified ID bridge: dss_enriched ↔ fusion row_id ↔ appendix gematria [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys_path = ROOT / "scripts"
import sys

sys.path.insert(0, str(ROOT))

from scripts.shadow_lane_gematria_common_v1 import (
    build_appendix_index,
    gematria_from_text,
    load_dss_enriched_by_id,
    load_json,
)

OUT_DEFAULT = ROOT / "reports/shadow_appendix_id_bridge_v1_latest.json"
APPENDIX = ROOT / "reports/shadow_lane_appendix_gematria_v1_latest.json"
FUSION = ROOT / "data/logos/manuscripts/fusion_unified_corpus_stage1_v1.jsonl"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build() -> dict[str, Any]:
    appendix = load_json(APPENDIX)
    appendix_index = build_appendix_index(appendix)
    dss_by_id = load_dss_enriched_by_id()

    bridges: list[dict[str, Any]] = []
    for eid, dss_row in sorted(dss_by_id.items()):
        text = str(dss_row.get("text") or "")
        appendix_hit = appendix_index.get(eid)
        bridges.append(
            {
                "primary_id": eid,
                "alias_ids": [eid],
                "lane": "dss",
                "appendix_hit": appendix_hit is not None,
                "gematria": (appendix_hit or {}).get("gematria") or gematria_from_text(text),
                "source_doc": dss_row.get("source_doc"),
                "resolve_path": "appendix" if appendix_hit else "dss_jsonl_compute",
            }
        )

    fusion_aliases = 0
    if FUSION.is_file():
        with FUSION.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                doc = json.loads(line)
                if str(doc.get("lane") or "") != "dss":
                    continue
                row_id = str(doc.get("row_id") or "")
                source_ref = str(doc.get("source_ref") or "")
                if not row_id:
                    continue
                appendix_hit = appendix_index.get(row_id) or appendix_index.get(source_ref)
                if not appendix_hit:
                    continue
                bridges.append(
                    {
                        "primary_id": row_id,
                        "alias_ids": [row_id, source_ref],
                        "lane": "dss",
                        "appendix_hit": True,
                        "gematria": appendix_hit.get("gematria") or {},
                        "source_doc": "fusion_unified",
                        "resolve_path": "fusion_dss_lane",
                    }
                )
                fusion_aliases += 1

    dss_enriched_hits = sum(1 for b in bridges if b["primary_id"].startswith("dss_enriched_") and b["appendix_hit"])

    return {
        "schema": "shadow_appendix_id_bridge_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "summary": {
            "total_bridge_rows": len(bridges),
            "dss_enriched_rows": len(dss_by_id),
            "dss_enriched_appendix_hits": dss_enriched_hits,
            "fusion_dss_alias_rows": fusion_aliases,
        },
        "bridges": bridges,
        "reproduce": "py scripts/build_shadow_appendix_id_bridge_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    sm = doc["summary"]
    ok = int(sm.get("dss_enriched_appendix_hits") or 0) >= int(sm.get("dss_enriched_rows") or 0) * 0.9
    print(json.dumps({"ok": ok, "summary": sm, "out": str(args.out.relative_to(ROOT))}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
