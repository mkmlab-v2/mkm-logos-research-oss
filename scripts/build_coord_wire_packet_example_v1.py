#!/usr/bin/env python3
"""Build SKU-COORD wire packet example from rib55 manifest + v2 stub contract."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/final/artifacts/rib55_angle_overlay_manifest_v1.json"
OUT = ROOT / "docs/final/artifacts/coord_wire_packet_example_v1_latest.json"
REPORT = ROOT / "reports/coord_wire_packet_example_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _token_proxy(text: str) -> int | None:
    try:
        import tiktoken

        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        return None


def main() -> int:
    sys.path.insert(0, str(ROOT))
    from scripts.rib55_angle_overlay_v1_lib import sha256_file

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    entry = manifest["entries"][0]
    layer = (entry.get("overlays") or [None])[0] or {}
    base = entry.get("base_image") or {}
    source = entry.get("source") or {}

    local_rel = base.get("local_path")
    base_sha = None
    base_bytes = None
    if local_rel:
        base_path = ROOT / local_rel
        if base_path.is_file():
            base_sha = sha256_file(base_path)
            base_bytes = base_path.stat().st_size

    coord_inject = {
        "entry_id": entry.get("entry_id"),
        "layer_id": layer.get("layer_id"),
        "coord_spec": manifest.get("coord_spec", "anatomy_overlay_coord_v1"),
        "points_norm": layer.get("points_norm"),
        "stroke": layer.get("stroke"),
        "label_text": layer.get("label_text"),
    }
    coord_wire_minimal = {
        "sku_class": "coord",
        "wire_mode": "anatomy_overlay_coord_v1",
        "base_asset_id": f"commons:{source.get('title', 'unknown')}",
        "base_sha256": base_sha,
        "coord_inject": coord_inject,
    }

    coord_json = json.dumps(coord_wire_minimal, ensure_ascii=False, separators=(",", ":"))
    full_image_token_proxy = _token_proxy(f"[PNG_BASE64_PLACEHOLDER_{base_bytes or 0}_bytes]")

    doc = {
        "schema": "coord_wire_packet_example_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "track_a_active_untouched": True,
        "boundary_ack": (
            "SKU-COORD wire example — bilateral base + short coord inject. "
            "Not v2 stub production path; MASK compress KPI must not merge (FAIL-COMP-004)."
        ),
        "ssot_pointers": {
            "rib55_manifest": "docs/final/artifacts/rib55_angle_overlay_manifest_v1.json",
            "sku_brief": "docs/final/artifacts/compression_sku_separation_brief_v1_latest.json",
            "hybrid_router_coord_modes": "docs/final/artifacts/compression_hybrid_router_spec_v1.json#sku_coord_wire_modes",
            "v2_openapi": "docs/final/openapi_token_compression_v2_draft.yaml",
        "v2_stub_lib": "scripts/coord_anatomy_overlay_wire_v1_lib.py",
        "v2_stub_route": "POST /v2/compress sku_class=coord → POST /v2/expand render",
        },
        "coord_wire_minimal": coord_wire_minimal,
        "v2_compress_request_example": {
            "sku_class": "coord",
            "loss_profile": "lossless_text",
            "routing_profile": "track_a_promoted",
            "text": coord_json,
            "emit_semantic_pointer": True,
            "notes": "HYPO: text field carries coord JSON, not masked prose bulk",
        },
        "token_proxy_cl100k": {
            "coord_wire_chars": len(coord_json),
            "coord_wire_tokens": _token_proxy(coord_json),
            "full_png_placeholder_tokens": full_image_token_proxy,
            "method": "tiktoken:cl100k_base",
            "caveat": "PNG token count is placeholder string only — illustrates order-of-magnitude, not on-wire base64",
        },
        "bilateral_pre_sync": {
            "required": True,
            "client_holds": ["base_image_bytes_or_cached_path", "manifest_entry_schema"],
            "server_or_peer_holds": "same base_sha256 + coord_spec version",
            "original_bulk_to_mkm_saas": False,
        },
        "reproduce": "py scripts/build_coord_wire_packet_example_v1.py",
    }

    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(payload, encoding="utf-8")
    REPORT.write_text(payload, encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(OUT), "coord_wire_tokens": doc["token_proxy_cl100k"]["coord_wire_tokens"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
