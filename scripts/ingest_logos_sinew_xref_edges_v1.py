#!/usr/bin/env python3
"""Ingest Sinew Tier-2 cross-references into logos_sinew_xref_edges [HYPO].

Reads sinew.sqlite connections (review_status='ok'). License gate: --ack-license-cc-by-4.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.logos_verse_ref_canonical_v1 import canonical_verse_ref

DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_sinew_xref_edges_v1.jsonl"
DEFAULT_MANIFEST = ROOT / "docs/final/artifacts/logos_sinew_xref_edges_v1_latest.json"
DEFAULT_REPORT = ROOT / "reports/logos_sinew_xref_ingest_v1_latest.json"
DEFAULT_SINEW_DIR = ROOT / "storage/external_kg/sinew_v1"
FIXTURE_DIR = ROOT / "tests/fixtures/sinew_xref_sample_v1"

LICENSE_ACK = "CC-BY-4.0"
EDGE_TYPE = "cross_reference"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def _normalize_weight(raw: Any) -> float:
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return 0.35
    if v <= 1.0:
        return max(0.0, min(1.0, v))
    return max(0.0, min(1.0, v / 100.0))


def build_edges_from_sqlite(
    db_path: Path,
    *,
    max_edges: int,
    min_weight: float,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    stats = {"rows_scanned": 0, "edges_built": 0, "skipped_bad_ref": 0, "skipped_low_weight": 0}
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    edge_i = 0

    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    try:
        cur = con.execute(
            """
            SELECT source_verse_id, target_verse_id, type, source, weight, review_status
            FROM connections
            WHERE review_status = 'ok'
            ORDER BY weight DESC
            """
        )
        for rec in cur:
            stats["rows_scanned"] += 1
            if len(rows) >= max_edges:
                break
            src = canonical_verse_ref(str(rec["source_verse_id"] or ""))
            dst = canonical_verse_ref(str(rec["target_verse_id"] or ""))
            if not src or not dst:
                stats["skipped_bad_ref"] += 1
                continue
            w = _normalize_weight(rec["weight"])
            if w < min_weight:
                stats["skipped_low_weight"] += 1
                continue
            prov_source = str(rec["source"] or "OpenBible")
            etype = str(rec["type"] or EDGE_TYPE)
            key = (src, dst, prov_source)
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                {
                    "schema": "logos_sinew_xref_edge_v1",
                    "edge_id": f"sinew_xref::{edge_i}",
                    "src_node_id": src,
                    "dst_node_id": dst,
                    "edge_type": etype,
                    "weight": w,
                    "hypothesis_tier": "B",
                    "research_only": True,
                    "source": "sinew_xref",
                    "provenance": {
                        "upstream_source": prov_source,
                        "review_status": str(rec["review_status"] or "ok"),
                        "raw_weight": rec["weight"],
                    },
                    "license": LICENSE_ACK,
                }
            )
            edge_i += 1
            stats["edges_built"] += 1
    finally:
        con.close()

    return rows, stats


def build_edges_from_fixture(fixture_dir: Path, *, max_edges: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    path = fixture_dir / "connections_sample.json"
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    stats = {"rows_scanned": len(doc), "edges_built": 0, "skipped_bad_ref": 0, "skipped_low_weight": 0}
    rows: list[dict[str, Any]] = []
    for i, rec in enumerate(doc[:max_edges]):
        src = canonical_verse_ref(str(rec.get("source_verse_id") or ""))
        dst = canonical_verse_ref(str(rec.get("target_verse_id") or ""))
        if not src or not dst:
            stats["skipped_bad_ref"] += 1
            continue
        rows.append(
            {
                "schema": "logos_sinew_xref_edge_v1",
                "edge_id": f"sinew_xref::fixture_{i}",
                "src_node_id": src,
                "dst_node_id": dst,
                "edge_type": str(rec.get("type") or EDGE_TYPE),
                "weight": _normalize_weight(rec.get("weight")),
                "hypothesis_tier": "B",
                "research_only": True,
                "source": "sinew_xref",
                "provenance": {
                    "upstream_source": str(rec.get("source") or "OpenBible"),
                    "review_status": "ok",
                    "raw_weight": rec.get("weight"),
                },
                "license": "fixture_offline_only",
            }
        )
        stats["edges_built"] += 1
    return rows, stats


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sinew-dir", type=Path, default=None)
    ap.add_argument("--use-fixture-sample", action="store_true")
    ap.add_argument("--ack-license-cc-by-4", action="store_true")
    ap.add_argument("--max-edges", type=int, default=150000)
    ap.add_argument("--min-weight", type=float, default=0.15)
    ap.add_argument("--out-jsonl", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--min-edges", type=int, default=3)
    args = ap.parse_args()

    if args.use_fixture_sample:
        rows, stats = build_edges_from_fixture(FIXTURE_DIR, max_edges=args.max_edges)
        sinew_dir = FIXTURE_DIR
        license_ack = "fixture_offline_only"
    elif args.sinew_dir:
        if not args.ack_license_cc_by_4:
            raise SystemExit("non-fixture ingest requires --ack-license-cc-by-4")
        db = args.sinew_dir / "sinew.sqlite"
        if not db.is_file():
            raise SystemExit(f"missing sqlite: {db}")
        rows, stats = build_edges_from_sqlite(db, max_edges=args.max_edges, min_weight=args.min_weight)
        sinew_dir = args.sinew_dir
        license_ack = LICENSE_ACK
    else:
        raise SystemExit("provide --sinew-dir or --use-fixture-sample")

    args.out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    args.out_jsonl.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + ("\n" if rows else ""),
        encoding="utf-8",
    )

    manifest = {
        "schema": "logos_sinew_xref_edges_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "edge_count": len(rows),
        "stats": stats,
        "note": "Sinew Tier-2 sourced cross-references; attributed not asserted.",
        "reproduce": "py scripts/ingest_logos_sinew_xref_edges_v1.py --sinew-dir storage/external_kg/sinew_v1 --ack-license-cc-by-4",
    }
    args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    report = {
        "schema": "logos_sinew_xref_ingest_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "license_ack": license_ack,
        "sinew_dir": _rel(sinew_dir),
        "stats": stats,
        "edges_built": len(rows),
        "out_jsonl": _rel(args.out_jsonl),
        "reproduce": manifest["reproduce"],
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    ok = len(rows) >= args.min_edges
    print(json.dumps({"ok": ok, "edges_built": len(rows), "stats": stats}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
