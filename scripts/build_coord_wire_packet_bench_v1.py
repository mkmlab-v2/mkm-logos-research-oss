#!/usr/bin/env python3
"""Build COORD wire packets for all rib55 manifest entries — token bench (FAIL-COMP-004 isolated)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/final/artifacts/rib55_angle_overlay_manifest_v1.json"
OUT = ROOT / "docs/final/artifacts/coord_wire_packet_bench_v1_latest.json"
REPORT = ROOT / "reports/coord_wire_packet_bench_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _token_proxy(text: str) -> int | None:
    try:
        import tiktoken

        return len(tiktoken.get_encoding("cl100k_base").encode(text))
    except Exception:
        return None


def build_wire_for_entry(entry: dict, manifest: dict, *, root: Path) -> dict:
    sys.path.insert(0, str(root))
    from scripts.rib55_angle_overlay_v1_lib import sha256_file

    layer = (entry.get("overlays") or [None])[0] or {}
    base = entry.get("base_image") or {}
    source = entry.get("source") or {}
    local_rel = base.get("local_path")
    base_sha = None
    if local_rel:
        base_path = root / local_rel
        if base_path.is_file():
            base_sha = sha256_file(base_path)

    coord_inject = {
        "entry_id": entry.get("entry_id"),
        "layer_id": layer.get("layer_id"),
        "coord_spec": manifest.get("coord_spec", "anatomy_overlay_coord_v1"),
        "points_norm": layer.get("points_norm"),
        "stroke": layer.get("stroke"),
        "label_text": layer.get("label_text"),
    }
    wire = {
        "sku_class": "coord",
        "wire_mode": "anatomy_overlay_coord_v1",
        "base_asset_id": f"commons:{source.get('title', 'unknown')}",
        "base_sha256": base_sha,
        "coord_inject": coord_inject,
    }
    wire_json = json.dumps(wire, ensure_ascii=False, separators=(",", ":"))
    return {
        "entry_id": entry.get("entry_id"),
        "layer_id": layer.get("layer_id"),
        "coord_wire_minimal": wire,
        "coord_wire_chars": len(wire_json),
        "coord_wire_tokens": _token_proxy(wire_json),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", type=Path, default=MANIFEST)
    args = ap.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    rows = [build_wire_for_entry(e, manifest, root=ROOT) for e in manifest.get("entries") or []]
    tokens = [r["coord_wire_tokens"] for r in rows if r.get("coord_wire_tokens") is not None]

    doc = {
        "schema": "coord_wire_packet_bench_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "entry_count": len(rows),
        "entries": rows,
        "aggregate": {
            "min_tokens": min(tokens) if tokens else None,
            "max_tokens": max(tokens) if tokens else None,
            "token_delta_max_minus_min": (max(tokens) - min(tokens)) if len(tokens) >= 2 else 0,
        },
        "boundary_ack": "SKU-COORD bench only — MASK KPI merge forbidden (FAIL-COMP-004)",
        "reproduce": "py scripts/build_coord_wire_packet_bench_v1.py",
    }

    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(payload, encoding="utf-8")
    REPORT.write_text(payload, encoding="utf-8")
    print(
        json.dumps(
            {"ok": True, "entry_count": len(rows), "aggregate": doc["aggregate"]},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
