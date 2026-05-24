#!/usr/bin/env python3
"""COMP-ANCHOR-06: export verse pools for top-N atoms from full-scan histogram."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCAN = ROOT / "reports/constitution/btrack_pilot/comp_anchor05_verse_pool_full_scan_v1.json"
OUT = ROOT / "reports/constitution/btrack_pilot/comp_anchor06_top_verse_pools_v1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scan-json", default=str(SCAN))
    parser.add_argument("--top-n", type=int, default=8)
    parser.add_argument("--max-verses-per-atom", type=int, default=25, help="cap pool list size")
    parser.add_argument("--out-json", default=str(OUT))
    args = parser.parse_args()

    scan_path = Path(args.scan_json)
    if not scan_path.is_absolute():
        scan_path = ROOT / scan_path
    if not scan_path.is_file():
        print(f"missing scan: {scan_path}", file=sys.stderr)
        return 1

    from scripts.resolve_logos_atom_anchor_verse_pool_v1 import (  # noqa: WPS433
        _resolve_paths_from_registry,
        build_verse_pool,
    )

    scan = json.loads(scan_path.read_text(encoding="utf-8"))
    tops = (scan.get("top_atoms_by_verse_hits") or [])[: max(1, args.top_n)]
    verse_path, codebook_path = _resolve_paths_from_registry()

    pools: list[dict[str, Any]] = []
    for row in tops:
        aid = str(row.get("atom_id") or "")
        if not aid:
            continue
        doc = build_verse_pool(aid, verse_jsonl=verse_path, codebook_json=codebook_path, max_rows=0)
        pool = list(doc.get("verse_pool") or [])
        if args.max_verses_per_atom > 0:
            pool = pool[: args.max_verses_per_atom]
        pools.append(
            {
                "atom_id": aid,
                "verses_with_hits_scan": row.get("verses_with_hits"),
                "verse_count": doc.get("verse_count"),
                "verses_scanned": doc.get("verses_scanned"),
                "codebook_known": doc.get("codebook_known"),
                "verse_pool_sample": pool,
            }
        )

    report = {
        "schema": "comp_anchor06_top_verse_pools_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "[HYPO]",
        "inputs": {"scan_json": str(scan_path.relative_to(ROOT)).replace("\\", "/")},
        "top_n": len(pools),
        "pools": pools,
    }
    out_path = Path(args.out_json)
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": out_path.name, "pools": len(pools)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
