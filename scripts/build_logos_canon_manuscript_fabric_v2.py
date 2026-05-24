#!/usr/bin/env python3
"""Build logos_canon_manuscript_fabric_v2: address/ink separation + bridge edges + wire routing."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.logos_canon_manuscript_fabric_v2 import (  # noqa: E402
    SCHEMA,
    VERSION,
    build_manuscript_bindings,
    build_virtual_bridge_edges,
    build_wire_routing_table,
)

DEFAULT_POLICY = ROOT / "data/logos/logos_gap_mt_only_policy_v1.jsonl"
DEFAULT_CLASSIFY = ROOT / "docs/final/artifacts/logos_gap_mt_only_residual_classify_v1_latest.json"
DEFAULT_MANIFEST = ROOT / "docs/final/artifacts/logos_corpus_manifest_v1_latest.json"
DEFAULT_VARIANT = ROOT / "docs/final/artifacts/logos_textual_variant_distance_v1_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_canon_manuscript_fabric_v2_latest.json"
DEFAULT_BRIDGES = ROOT / "data/logos/logos_variant_omission_bridge_edges_v2.jsonl"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path.resolve().as_posix())


def _load_gap_ids(policy_path: Path, classify_path: Path) -> list[str]:
    ids: list[str] = []
    if policy_path.is_file():
        for line in policy_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            vid = str(row.get("verse_id") or "").strip()
            if vid:
                ids.append(vid)
    if ids:
        return sorted(set(ids))
    if classify_path.is_file():
        doc = json.loads(classify_path.read_text(encoding="utf-8"))
        return sorted(str(v.get("verse_id")) for v in doc.get("verses") or [] if v.get("verse_id"))
    return []


def _variant_index(path: Path) -> dict[str, dict[str, Any]]:
    if not path.is_file():
        return {}
    doc = json.loads(path.read_text(encoding="utf-8"))
    return {str(e["verse_id"]): e for e in doc.get("entries") or [] if e.get("verse_id")}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--policy-jsonl", type=Path, default=DEFAULT_POLICY)
    ap.add_argument("--classify-json", type=Path, default=DEFAULT_CLASSIFY)
    ap.add_argument("--manifest-json", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--variant-json", type=Path, default=DEFAULT_VARIANT)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--bridges-jsonl", type=Path, default=DEFAULT_BRIDGES)
    args = ap.parse_args()

    gap_ids = _load_gap_ids(args.policy_jsonl, args.classify_json)
    if not gap_ids:
        print("no gap verse ids found", file=sys.stderr)
        return 2

    manifest_snap: dict[str, Any] = {}
    canon_count = 31102
    if args.manifest_json.is_file():
        manifest_snap = json.loads(args.manifest_json.read_text(encoding="utf-8"))
        canon_count = int(manifest_snap.get("verse_count") or canon_count)

    variant_ix = _variant_index(args.variant_json)
    bindings = build_manuscript_bindings(gap_ids, variant_ix)
    bridges = build_virtual_bridge_edges(gap_ids)
    wire_table = build_wire_routing_table(gap_ids)

    args.bridges_jsonl.parent.mkdir(parents=True, exist_ok=True)
    args.bridges_jsonl.write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in bridges) + ("\n" if bridges else ""),
        encoding="utf-8",
    )

    doc: dict[str, Any] = {
        "schema": SCHEMA,
        "version": VERSION,
        "ts_utc": _utc_now(),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "canonical_address_layer": {
            "verse_count": canon_count,
            "manifest_path": _rel(args.manifest_json) if args.manifest_json.is_file() else None,
            "manifest_snapshot_schema": manifest_snap.get("schema"),
            "role": "index_only_no_ink",
            "gap_nt_textual_variant_count": len(gap_ids),
            "gap_verse_ids": gap_ids,
        },
        "manuscript_instances": {
            "instances": [
                {
                    "instance_id": "sblgnt_bhs_v2_core",
                    "tradition": "MT_critical",
                    "corpus_type": "canonical",
                    "default_primary": True,
                },
                {
                    "instance_id": "tr_kjv_textual_variant_v1",
                    "tradition": "TR_KJV_versification",
                    "corpus_type": "textual_variant_satellite",
                    "default_primary": False,
                    "forbidden_merge_into": ["verse_decoded_v2_complete_v1.jsonl"],
                },
            ],
            "bindings": bindings,
        },
        "virtual_bridge_edges": {
            "edge_type": "variant_omission_bridge_v2",
            "count": len(bridges),
            "jsonl_path": _rel(args.bridges_jsonl),
        },
        "wire_routing": {
            "flag_re_route_tr_bit": 1,
            "by_verse_id": wire_table,
        },
        "track_wall": {
            "a_track_auto_promotion": False,
            "ready_for_external_send": False,
            "core_corpus_sha_unchanged": True,
        },
        "inputs": {
            "policy_jsonl": _rel(args.policy_jsonl),
            "classify_json": _rel(args.classify_json) if args.classify_json.is_file() else None,
            "variant_json": _rel(args.variant_json) if args.variant_json.is_file() else None,
        },
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": _rel(args.output), "gap_count": len(gap_ids), "bridge_count": len(bridges)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
