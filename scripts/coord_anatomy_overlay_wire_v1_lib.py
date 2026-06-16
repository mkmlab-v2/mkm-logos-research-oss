# -*- coding: utf-8 -*-
"""[HYPO] SKU-COORD anatomy overlay wire — parse, compact, expand via rib55 renderer."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
COORD_WIRE_KEY = "coord_anatomy_overlay_wire_v1"
WIRE_MODE = "anatomy_overlay_coord_v1"
COMPACT_PREFIX = "[COORD:anatomy:v1:"


def parse_coord_wire_text(text: str) -> dict[str, Any] | None:
    raw = (text or "").strip()
    if not raw:
        return None
    if raw.startswith("{"):
        try:
            doc = json.loads(raw)
        except json.JSONDecodeError:
            return None
        if doc.get("wire_mode") == WIRE_MODE or doc.get("sku_class") == "coord":
            return doc
        return None
    if raw.startswith(COMPACT_PREFIX) and raw.endswith("]"):
        return expand_compact_coord_wire(raw)
    return None


def expand_compact_coord_wire(compact: str) -> dict[str, Any] | None:
    """Decode ``[COORD:anatomy:v1:{entry_id}:{sha8}]`` — full wire must live in residual_meta."""
    inner = compact[len(COMPACT_PREFIX) : -1]
    parts = inner.split(":")
    if len(parts) < 2:
        return None
    entry_id, sha8 = parts[0], parts[1]
    return {
        "sku_class": "coord",
        "wire_mode": WIRE_MODE,
        "entry_id": entry_id,
        "base_sha256_short": sha8,
        "_compact_only": True,
    }


def compact_coord_wire(wire: dict[str, Any]) -> str:
    entry_id = str(
        wire.get("entry_id")
        or (wire.get("coord_inject") or {}).get("entry_id")
        or "pilot"
    )
    sha = str(wire.get("base_sha256") or "")
    sha8 = sha[:8] if sha else "00000000"
    return f"{COMPACT_PREFIX}{entry_id}:{sha8}]"


def _entry_from_wire(wire: dict[str, Any]) -> dict[str, Any]:
    inject = wire.get("coord_inject") if isinstance(wire.get("coord_inject"), dict) else {}
    local_path = None
    title = "Ninth rib lateral2.png"
    if wire.get("base_asset_id", "").startswith("commons:"):
        title = str(wire["base_asset_id"]).split(":", 1)[1]
    fixture_map = {
        "Ninth rib lateral2.png": "data/anatomy/fixtures/ninth_rib_lateral2.png",
        "Second rib lateral2.png": "data/anatomy/fixtures/second_rib_lateral2.png",
    }
    local_path = fixture_map.get(title)
    entry_id = str(wire.get("entry_id") or inject.get("entry_id") or "coord_expand")
    layer_id = str(inject.get("layer_id") or "coord_layer")
    return {
        "entry_id": entry_id,
        "base_image": {"local_path": local_path},
        "source": {"title": title},
        "overlays": [
            {
                "layer_id": layer_id,
                "type": "angle_arc",
                "angle_deg": inject.get("angle_deg"),
                "points_norm": inject.get("points_norm") or [],
                "stroke": inject.get("stroke", "#E11D48"),
                "label_text": inject.get("label_text", "coord overlay — HYPO"),
            }
        ],
    }


def materialize_coord_wire(
    wire: dict[str, Any],
    *,
    workspace_root: Path = ROOT,
    out_dir: Path | None = None,
) -> dict[str, Any]:
    from scripts.rib55_angle_overlay_v1_lib import render_entry_overlay, resolve_base_image, sha256_file

    if wire.get("_compact_only"):
        raise ValueError("compact coord wire requires full wire in residual_meta.coord_anatomy_overlay_wire_v1")

    entry = _entry_from_wire(wire)
    base_path = resolve_base_image(entry, workspace_root=workspace_root, fetch=False)
    eid = str(entry.get("entry_id", "coord"))
    out_root = out_dir or (workspace_root / "reports")
    out_path = out_root / f"rib55_v2stub_expand_{eid}_latest.png"
    report = render_entry_overlay(entry, base_path, out_path)
    report["coord_wire_mode"] = WIRE_MODE
    report["base_sha256_expected"] = wire.get("base_sha256")
    if wire.get("base_sha256") and report.get("base_sha256") != wire.get("base_sha256"):
        report["base_sha256_match"] = False
    else:
        report["base_sha256_match"] = True
    report["output_sha256"] = sha256_file(out_path)
    return report


def expand_coord_wire_to_text(
    wire: dict[str, Any],
    *,
    workspace_root: Path = ROOT,
) -> tuple[str, dict[str, Any]]:
    report = materialize_coord_wire(wire, workspace_root=workspace_root)
    rel_out = Path(report["output"]).relative_to(workspace_root).as_posix()
    payload = {
        "schema": "coord_anatomy_overlay_expand_v1",
        "research_only": True,
        "render_report": {**report, "output": rel_out},
    }
    text = json.dumps(payload, ensure_ascii=False)
    flags = {
        "reassembly": "coord_anatomy_overlay_wire_v1",
        "source": COORD_WIRE_KEY,
        "exact_restore_ok": bool(report.get("base_sha256_match", True)),
        "roundtrip_path": "manifest_to_render_v1",
        "wire_mode": WIRE_MODE,
        "research_only": True,
    }
    return text, flags
