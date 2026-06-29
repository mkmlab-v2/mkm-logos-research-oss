#!/usr/bin/env python3
"""Ingest Theographic people/places/events → verse entity edges [HYPO]."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.logos_verse_ref_canonical_v1 import canonical_verse_ref

DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_theographic_entity_edges_v1.jsonl"
DEFAULT_MANIFEST = ROOT / "docs/final/artifacts/logos_theographic_entity_edges_v1_latest.json"
DEFAULT_REPORT = ROOT / "reports/logos_theographic_entity_ingest_v1_latest.json"
DEFAULT_DIR = ROOT / "storage/external_kg/theographic_v1"
FIXTURE_DIR = ROOT / "tests/fixtures/theographic_entity_sample_v1"

LICENSE_ACK = "CC-BY-SA-4.0"
ENTITY_KINDS = (
    ("people.json", "person", "personLookup", "name", "THEOGRAPHIC_PERSON_VERSE"),
    ("places.json", "place", "placeLookup", "displayTitle", "THEOGRAPHIC_PLACE_VERSE"),
    ("events.json", "event", "eventLookup", "eventGroup", "THEOGRAPHIC_EVENT_VERSE"),
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def _load_entity_index(path: Path, *, lookup_field: str, name_field: str, kind: str) -> dict[str, dict[str, str]]:
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(doc, list):
        return {}
    out: dict[str, dict[str, str]] = {}
    for row in doc:
        if not isinstance(row, dict):
            continue
        rec_id = str(row.get("id") or "")
        fields = row.get("fields") if isinstance(row.get("fields"), dict) else {}
        lookup = str(fields.get(lookup_field) or fields.get("slug") or rec_id)
        name = str(fields.get(name_field) or fields.get("kjvName") or lookup)
        if rec_id:
            out[rec_id] = {"kind": kind, "lookup": lookup, "name": name}
    return out


def build_edges_from_dir(
    theographic_dir: Path,
    *,
    max_edges: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    stats = {
        "verses_scanned": 0,
        "edges_built": 0,
        "skipped_bad_ref": 0,
        "by_kind": {"person": 0, "place": 0, "event": 0},
    }
    entity_maps: dict[str, dict[str, str]] = {}
    for file_name, kind, lookup_field, name_field, _etype in ENTITY_KINDS:
        path = theographic_dir / file_name
        if path.is_file():
            entity_maps.update(_load_entity_index(path, lookup_field=lookup_field, name_field=name_field, kind=kind))

    verses_path = theographic_dir / "verses.json"
    verses = json.loads(verses_path.read_text(encoding="utf-8-sig"))
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    edge_i = 0

    field_map = {"person": "people", "place": "places", "event": "event"}

    for verse_row in verses:
        stats["verses_scanned"] += 1
        if len(rows) >= max_edges:
            break
        fields = verse_row.get("fields") if isinstance(verse_row.get("fields"), dict) else {}
        verse_ref = canonical_verse_ref(str(fields.get("osisRef") or ""))
        if not verse_ref:
            stats["skipped_bad_ref"] += 1
            continue
        for _file_name, kind, _lookup_field, _name_field, etype in ENTITY_KINDS:
            for rec_id in fields.get(field_map[kind]) or []:
                if len(rows) >= max_edges:
                    break
                meta = entity_maps.get(str(rec_id))
                if not meta:
                    continue
                src = f"entity:{meta['kind']}:{meta['lookup']}"
                key = (src, verse_ref, etype)
                if key in seen:
                    continue
                seen.add(key)
                rows.append(
                    {
                        "schema": "logos_theographic_entity_edge_v1",
                        "edge_id": f"theographic_entity::{edge_i}",
                        "src_node_id": src,
                        "dst_node_id": verse_ref,
                        "edge_type": etype,
                        "entity_kind": meta["kind"],
                        "entity_name": meta["name"],
                        "entity_lookup": meta["lookup"],
                        "weight": 1.0,
                        "hypothesis_tier": "B",
                        "research_only": True,
                        "source": "theographic",
                        "provenance": {"upstream_rec_id": rec_id, "osis_ref": fields.get("osisRef")},
                        "license": LICENSE_ACK,
                    }
                )
                stats["edges_built"] += 1
                stats["by_kind"][kind] += 1
                edge_i += 1

    return rows, stats


def build_edges_from_fixture(fixture_dir: Path, *, max_edges: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    theographic_dir = fixture_dir
    return build_edges_from_dir(theographic_dir, max_edges=max_edges)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--theographic-dir", type=Path, default=None)
    ap.add_argument("--use-fixture-sample", action="store_true")
    ap.add_argument("--ack-license-cc-by-sa-4", action="store_true")
    ap.add_argument("--max-edges", type=int, default=150000)
    ap.add_argument("--out-jsonl", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--min-edges", type=int, default=3)
    args = ap.parse_args()

    if args.use_fixture_sample:
        rows, stats = build_edges_from_fixture(FIXTURE_DIR, max_edges=args.max_edges)
        src_dir = FIXTURE_DIR
        license_ack = "fixture_offline_only"
    elif args.theographic_dir:
        if not args.ack_license_cc_by_sa_4:
            raise SystemExit("non-fixture ingest requires --ack-license-cc-by-sa-4")
        rows, stats = build_edges_from_dir(args.theographic_dir, max_edges=args.max_edges)
        src_dir = args.theographic_dir
        license_ack = LICENSE_ACK
    else:
        raise SystemExit("provide --theographic-dir or --use-fixture-sample")

    args.out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    args.out_jsonl.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + ("\n" if rows else ""),
        encoding="utf-8",
    )

    manifest = {
        "schema": "logos_theographic_entity_edges_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "edge_count": len(rows),
        "stats": stats,
        "note": "Theographic entity→verse edges; attributed not asserted.",
        "reproduce": "py scripts/ingest_logos_theographic_entity_edges_v1.py --theographic-dir storage/external_kg/theographic_v1 --ack-license-cc-by-sa-4",
    }
    args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    report = {
        "schema": "logos_theographic_entity_ingest_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "license_ack": license_ack,
        "theographic_dir": _rel(src_dir),
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
