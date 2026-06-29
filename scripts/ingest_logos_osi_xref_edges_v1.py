#!/usr/bin/env python3
"""Ingest OSI graph/edges.jsonl into logos_osi_xref_edges [HYPO]."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.logos_osi_verse_id_v1 import osi_node_id_to_canonical

DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_osi_xref_edges_v1.jsonl"
DEFAULT_MANIFEST = ROOT / "docs/final/artifacts/logos_osi_xref_edges_v1_latest.json"
DEFAULT_REPORT = ROOT / "reports/logos_osi_xref_ingest_v1_latest.json"
DEFAULT_OSI_DIR = ROOT / "storage/external_kg/osi_v1"
FIXTURE_DIR = ROOT / "tests/fixtures/osi_xref_sample_v1"

LICENSE_ACK = "MIT+PD"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def _normalize_weight(rec: dict[str, Any]) -> float:
    if rec.get("confidence") is not None:
        try:
            return max(0.0, min(1.0, float(rec["confidence"])))
        except (TypeError, ValueError):
            pass
    if rec.get("votes") is not None:
        try:
            return max(0.0, min(1.0, float(rec["votes"]) / 100.0))
        except (TypeError, ValueError):
            pass
    return 0.35


def build_edges_from_jsonl(
    edges_path: Path,
    *,
    max_edges: int,
    min_weight: float,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    stats = {"rows_scanned": 0, "edges_built": 0, "skipped_bad_ref": 0, "skipped_low_weight": 0}
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    edge_i = 0

    with edges_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            stats["rows_scanned"] += 1
            if len(rows) >= max_edges:
                break
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            src = osi_node_id_to_canonical(str(rec.get("from") or ""))
            dst = osi_node_id_to_canonical(str(rec.get("to") or ""))
            if not src or not dst:
                stats["skipped_bad_ref"] += 1
                continue
            w = _normalize_weight(rec)
            if w < min_weight:
                stats["skipped_low_weight"] += 1
                continue
            etype = str(rec.get("type") or "cross_reference")
            prov_source = str(rec.get("source") or "openbible_crossrefs")
            key = (src, dst, etype)
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                {
                    "schema": "logos_osi_xref_edge_v1",
                    "edge_id": f"osi_xref::{edge_i}",
                    "src_node_id": src,
                    "dst_node_id": dst,
                    "edge_type": etype,
                    "weight": w,
                    "hypothesis_tier": "B",
                    "research_only": True,
                    "source": "osi_xref",
                    "provenance": {
                        "upstream_source": prov_source,
                        "raw_from": rec.get("from"),
                        "raw_to": rec.get("to"),
                        "raw_votes": rec.get("votes"),
                        "raw_confidence": rec.get("confidence"),
                    },
                    "license": LICENSE_ACK,
                }
            )
            edge_i += 1
            stats["edges_built"] += 1

    return rows, stats


def build_edges_from_fixture(fixture_dir: Path, *, max_edges: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    path = fixture_dir / "edges_sample.jsonl"
    stats = {"rows_scanned": 0, "edges_built": 0, "skipped_bad_ref": 0, "skipped_low_weight": 0}
    rows: list[dict[str, Any]] = []
    for i, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines()):
        if not line.strip() or len(rows) >= max_edges:
            continue
        stats["rows_scanned"] += 1
        rec = json.loads(line)
        src = osi_node_id_to_canonical(str(rec.get("from") or ""))
        dst = osi_node_id_to_canonical(str(rec.get("to") or ""))
        if not src or not dst:
            stats["skipped_bad_ref"] += 1
            continue
        rows.append(
            {
                "schema": "logos_osi_xref_edge_v1",
                "edge_id": f"osi_xref::fixture_{i}",
                "src_node_id": src,
                "dst_node_id": dst,
                "edge_type": str(rec.get("type") or "cross_reference"),
                "weight": _normalize_weight(rec),
                "hypothesis_tier": "B",
                "research_only": True,
                "source": "osi_xref",
                "provenance": {
                    "upstream_source": str(rec.get("source") or "openbible_crossrefs"),
                    "raw_from": rec.get("from"),
                    "raw_to": rec.get("to"),
                },
                "license": "fixture_offline_only",
            }
        )
        stats["edges_built"] += 1
    return rows, stats


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--osi-dir", type=Path, default=None)
    ap.add_argument("--use-fixture-sample", action="store_true")
    ap.add_argument("--ack-license-mit-pd", action="store_true")
    ap.add_argument("--max-edges", type=int, default=150000)
    ap.add_argument("--min-weight", type=float, default=0.15)
    ap.add_argument("--out-jsonl", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--min-edges", type=int, default=3)
    args = ap.parse_args()

    if args.use_fixture_sample:
        rows, stats = build_edges_from_fixture(FIXTURE_DIR, max_edges=args.max_edges)
        osi_dir = FIXTURE_DIR
        license_ack = "fixture_offline_only"
    elif args.osi_dir:
        if not args.ack_license_mit_pd:
            raise SystemExit("non-fixture ingest requires --ack-license-mit-pd")
        edges_path = args.osi_dir / "edges.jsonl"
        if not edges_path.is_file():
            raise SystemExit(f"missing edges.jsonl: {edges_path}")
        rows, stats = build_edges_from_jsonl(edges_path, max_edges=args.max_edges, min_weight=args.min_weight)
        osi_dir = args.osi_dir
        license_ack = LICENSE_ACK
    else:
        raise SystemExit("provide --osi-dir or --use-fixture-sample")

    args.out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    args.out_jsonl.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + ("\n" if rows else ""),
        encoding="utf-8",
    )

    manifest = {
        "schema": "logos_osi_xref_edges_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "edge_count": len(rows),
        "stats": stats,
        "note": "OSI graph edges; attributed not asserted.",
        "reproduce": "py scripts/ingest_logos_osi_xref_edges_v1.py --osi-dir storage/external_kg/osi_v1 --ack-license-mit-pd",
    }
    args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    report = {
        "schema": "logos_osi_xref_ingest_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "license_ack": license_ack,
        "osi_dir": _rel(osi_dir),
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
