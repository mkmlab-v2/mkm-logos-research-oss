# -*- coding: utf-8 -*-
"""[HYPO] Han Vocology larynx point-label overlay library."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "docs/final/artifacts/han_vocology_overlay_manifest_v1.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/han_vocology_fig12_larynx_cv23_overlay_v1_latest.png"


def load_manifest(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "han_vocology_overlay_manifest_v1":
        raise ValueError(f"unexpected manifest schema: {data.get('schema')}")
    return data


def save_manifest(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _hex_to_rgb(color: str) -> tuple[int, int, int]:
    c = color.lstrip("#")
    if len(c) != 6:
        return (192, 57, 43)
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)


def _norm_to_px(point: list[float], width: int, height: int) -> tuple[int, int]:
    x = max(0.0, min(1.0, float(point[0])))
    y = max(0.0, min(1.0, float(point[1])))
    return int(round(x * (width - 1))), int(round(y * (height - 1)))


def find_entry(manifest: dict[str, Any], entry_id: str | None) -> dict[str, Any]:
    entries = manifest.get("entries") or []
    if not entries:
        raise ValueError("manifest has no entries")
    if entry_id is None:
        return entries[0]
    for entry in entries:
        if entry.get("entry_id") == entry_id:
            return entry
    raise ValueError(f"entry_id not found: {entry_id}")


def render_point_labels(
    entry: dict[str, Any],
    base_image_path: Path,
    out_path: Path,
) -> dict[str, Any]:
    from PIL import Image, ImageDraw, ImageFont

    from scripts.rib55_angle_overlay_v1_lib import sha256_file

    with Image.open(base_image_path) as im:
        base = im.convert("RGBA")
        width, height = base.size
        draw = ImageDraw.Draw(base)

        try:
            font = ImageFont.truetype("malgun.ttf", 16)
            font_small = ImageFont.truetype("malgun.ttf", 11)
        except OSError:
            font = ImageFont.load_default()
            font_small = font

        title = entry.get("title_ko") or "CV23·CV22 교육용"
        draw.rectangle([0, 0, width, 28], fill=(0, 0, 0, 150))
        draw.text((8, 6), title, fill=(255, 255, 255), font=font_small)

        for overlay in entry.get("overlays") or []:
            if overlay.get("type") != "point_label":
                continue
            point = overlay.get("point_norm") or [0.5, 0.5]
            px = _norm_to_px(point, width, height)
            color = _hex_to_rgb(str(overlay.get("color", "#c0392b")))
            label = str(overlay.get("label", ""))
            r = 6
            draw.ellipse([px[0] - r, px[1] - r, px[0] + r, px[1] + r], outline=color, width=2)
            draw.line([px[0], px[1], px[0] + 24, px[1] - 18], fill=color, width=2)
            draw.text((px[0] + 26, px[1] - 22), label, fill=color, font=font)

        footer = str(entry.get("footer_ko") or "[교육용·비진단]")
        source = entry.get("source") or {}
        if source.get("attribution_text"):
            footer = f"{footer} | {source['attribution_text']}"
        footer_h = 48
        draw.rectangle([0, height - footer_h, width, height], fill=(0, 0, 0, 160))
        draw.text((8, height - footer_h + 8), footer[:140], fill=(255, 255, 255), font=font_small)

        out_path.parent.mkdir(parents=True, exist_ok=True)
        base.convert("RGB").save(out_path, format="PNG")

    return {
        "entry_id": entry.get("entry_id"),
        "fig_registry_id": entry.get("fig_registry_id"),
        "base_image": str(base_image_path),
        "base_sha256": sha256_file(base_image_path),
        "output": str(out_path),
        "output_sha256": sha256_file(out_path),
        "width": width,
        "height": height,
        "deterministic": True,
        "generative_anatomy": False,
    }


def render_from_manifest(
    manifest_path: Path,
    *,
    entry_id: str | None = None,
    out_path: Path | None = None,
    fetch_base: bool = False,
    update_manifest: bool = False,
    workspace_root: Path = ROOT,
) -> dict[str, Any]:
    from scripts.rib55_angle_overlay_v1_lib import resolve_base_image, sha256_file

    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    manifest = load_manifest(manifest_path)
    entry = find_entry(manifest, entry_id)
    eid = str(entry.get("entry_id", "larynx_pilot"))

    base_path = resolve_base_image(entry, workspace_root=workspace_root, fetch=fetch_base)
    rel_base = base_path.relative_to(workspace_root).as_posix()
    entry.setdefault("base_image", {})
    entry["base_image"]["local_path"] = rel_base
    entry["base_image"]["sha256"] = sha256_file(base_path)
    entry["base_image"]["fetch_status"] = "downloaded" if fetch_base else "cached"
    prior = str(entry.get("status") or "")
    if prior.startswith("adjudicated") or entry.get("adjudication"):
        entry["status"] = prior
    else:
        entry["status"] = "rendered_pending_adjudication"

    if out_path is None:
        out_path = DEFAULT_OUT

    report = render_point_labels(entry, base_path, out_path)
    report["manifest"] = str(manifest_path)
    report["status"] = entry["status"]
    report["send_gate"] = manifest.get("send_gate", "HOLD")
    report["generated_at"] = generated_at

    manifest.setdefault("verification", {})
    manifest["verification"].update(
        {
            "render_script": "scripts/render_han_vocology_larynx_overlay_v1.py",
            "last_exit_code": 0,
            "last_verified_at": generated_at,
            "last_output": out_path.relative_to(workspace_root).as_posix(),
            "last_output_sha256": report["output_sha256"],
        }
    )

    if update_manifest:
        save_manifest(manifest_path, manifest)

    return report
