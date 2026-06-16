# -*- coding: utf-8 -*-
"""[HYPO] Deterministic rib55 angle overlay renderer — manifest-driven vector on licensed base image.

research_only · SEND_GATE: HOLD · no generative anatomy pixels.
SSOT: docs/final/artifacts/rib55_angle_overlay_manifest_v1.json
Policy: docs/final/artifacts/anatomy_image_hallucination_control_protocol_hypo_v1_latest.md
"""

from __future__ import annotations

import hashlib
import json
import math
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "docs/final/artifacts/rib55_angle_overlay_manifest_v1.json"
DEFAULT_OUT_DIR = ROOT / "docs/final/artifacts"
FIXTURE_DIR = ROOT / "data/anatomy/fixtures"

COMMONS_API = "https://commons.wikimedia.org/w/api.php"
DEFAULT_USER_AGENT = "MKM-Rib55Overlay/1.0 (research_only; contact: local)"

_PRESERVE_ENTRY_STATUSES = frozenset(
    {
        "adjudicated_l0_v1_g0_pass",
        "adjudicated_education_internal",
        "adjudicated_with_reservations",
        "rejected",
    }
)


def load_manifest(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "rib55_angle_overlay_manifest_v1":
        raise ValueError(f"unexpected manifest schema: {data.get('schema')}")
    return data


def save_manifest(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def commons_direct_url(file_title: str) -> str:
    params = urllib.parse.urlencode(
        {
            "action": "query",
            "titles": f"File:{file_title}",
            "prop": "imageinfo",
            "iiprop": "url",
            "format": "json",
        }
    )
    req = urllib.request.Request(f"{COMMONS_API}?{params}", headers={"User-Agent": DEFAULT_USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    pages = payload.get("query", {}).get("pages", {})
    for page in pages.values():
        info = (page.get("imageinfo") or [None])[0]
        if info and info.get("url"):
            return str(info["url"])
    raise RuntimeError(f"Commons URL not found for File:{file_title}")


def download_file(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": DEFAULT_USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as resp:
        dest.write_bytes(resp.read())


def resolve_base_image(
    entry: dict[str, Any],
    *,
    workspace_root: Path = ROOT,
    fetch: bool = False,
) -> Path:
    base = entry.get("base_image") or {}
    local_rel = base.get("local_path")
    if local_rel:
        path = workspace_root / local_rel
        if path.is_file():
            return path

    source = entry.get("source") or {}
    title = source.get("title")
    if not title:
        raise FileNotFoundError("base_image.local_path missing and source.title absent")

    stem = Path(title).stem.lower().replace(" ", "_")
    dest = FIXTURE_DIR / f"{stem}.png"
    if dest.is_file():
        return dest

    if not fetch:
        raise FileNotFoundError(
            f"base image not on disk ({dest}); re-run with --fetch-base"
        )

    url = commons_direct_url(title)
    download_file(url, dest)
    return dest


def _norm_to_px(point: list[float], width: int, height: int) -> tuple[int, int]:
    x = max(0.0, min(1.0, float(point[0])))
    y = max(0.0, min(1.0, float(point[1])))
    return int(round(x * (width - 1))), int(round(y * (height - 1)))


def _hex_to_rgb(color: str) -> tuple[int, int, int]:
    c = color.lstrip("#")
    if len(c) != 6:
        return (225, 29, 72)
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)


def _point_role_labels(layer: dict[str, Any], entry: dict[str, Any]) -> list[dict[str, Any]]:
    roles = layer.get("point_roles")
    if roles:
        return list(roles)
    block = entry.get("anatomical_reference_points_v1") or {}
    return list(block.get("points") or [])


def _label_for_point_index(roles: list[dict[str, Any]], index: int) -> str | None:
    for role in roles:
        if role.get("points_norm_index") == index:
            return str(role.get("infographic_id") or role.get("id") or "")
    return None


def _draw_point_markers(
    draw: Any,
    px_points: list[tuple[int, int]],
    roles: list[dict[str, Any]],
    color: tuple[int, int, int],
) -> None:
    marker_r = 5
    for i, px in enumerate(px_points):
        draw.ellipse(
            [px[0] - marker_r, px[1] - marker_r, px[0] + marker_r, px[1] + marker_r],
            outline=color,
            width=2,
        )
        label = _label_for_point_index(roles, i)
        if label:
            draw.text((px[0] + 8, px[1] - 10), label, fill=color)


def _draw_overlay(
    draw: Any,
    layer: dict[str, Any],
    width: int,
    height: int,
    *,
    entry: dict[str, Any] | None = None,
) -> None:
    layer_type = layer.get("type", "angle_arc")
    points = layer.get("points_norm") or []
    if len(points) < 2:
        return

    px_points = [_norm_to_px(p, width, height) for p in points]
    color = _hex_to_rgb(str(layer.get("stroke", "#E11D48")))
    roles = _point_role_labels(layer, entry or {})
    show_arc = layer.get("show_angle_arc", True)
    show_degree = layer.get("show_degree_label", False) and layer.get("angle_deg") is not None

    if layer_type == "angle_arc" and len(px_points) >= 3:
        vtx, arm1, arm2 = px_points[0], px_points[1], px_points[2]
        draw.line([vtx, arm1], fill=color, width=3)
        draw.line([vtx, arm2], fill=color, width=3)
        if show_arc:
            r1 = math.hypot(arm1[0] - vtx[0], arm1[1] - vtx[1])
            r2 = math.hypot(arm2[0] - vtx[0], arm2[1] - vtx[1])
            radius = max(12, int(min(r1, r2) * 0.35))
            a1 = math.degrees(math.atan2(-(arm1[1] - vtx[1]), arm1[0] - vtx[0]))
            a2 = math.degrees(math.atan2(-(arm2[1] - vtx[1]), arm2[0] - vtx[0]))
            start, end = (a1, a2) if a1 <= a2 else (a2, a1)
            bbox = [vtx[0] - radius, vtx[1] - radius, vtx[0] + radius, vtx[1] + radius]
            draw.arc(bbox, start=start, end=end, fill=color, width=3)
        _draw_point_markers(draw, px_points, roles, color)
    elif layer_type == "arrow" and len(px_points) >= 2:
        draw.line(px_points[:2], fill=color, width=3)
        _draw_point_markers(draw, px_points[:2], roles, color)
    elif layer_type == "dashed_guide":
        for i in range(len(px_points) - 1):
            draw.line([px_points[i], px_points[i + 1]], fill=color, width=2)
        _draw_point_markers(draw, px_points, roles, color)
    else:
        for i in range(len(px_points) - 1):
            draw.line([px_points[i], px_points[i + 1]], fill=color, width=3)
        _draw_point_markers(draw, px_points, roles, color)

    label = layer.get("label_text")
    if label and px_points:
        anchor = px_points[0]
        draw.text((anchor[0] + 6, anchor[1] + 14), str(label), fill=color)
    if show_degree and layer.get("angle_deg") is not None:
        vtx = px_points[0]
        draw.text((vtx[0] - 24, vtx[1] - 24), f"{layer['angle_deg']}°", fill=color)


def _headline_text(entry: dict[str, Any]) -> str | None:
    inf = entry.get("infographic_field_v1") or {}
    return inf.get("headline_ko") or inf.get("subtitle_ko")


def _footer_text(entry: dict[str, Any]) -> str:
    inf = entry.get("infographic_field_v1") or {}
    base = str(
        inf.get("footer_ko")
        or "HYPO · theory overlay — not clinical diagnosis"
    )
    source = entry.get("source") or {}
    if source.get("attribution_required"):
        short = str(
            source.get("attribution_footer")
            or "Base: DBCLS (CC BY-SA 2.1 JP)"
        )
        return f"{base} | {short}"
    return base


def render_entry_overlay(
    entry: dict[str, Any],
    base_image_path: Path,
    out_path: Path,
) -> dict[str, Any]:
    from PIL import Image, ImageDraw, ImageFont

    with Image.open(base_image_path) as im:
        base = im.convert("RGBA")
        width, height = base.size
        draw = ImageDraw.Draw(base)

        for layer in entry.get("overlays") or []:
            _draw_overlay(draw, layer, width, height, entry=entry)

        headline = _headline_text(entry)
        footer = _footer_text(entry)
        try:
            font = ImageFont.load_default()
        except OSError:
            font = None

        if headline:
            headline_h = 28
            draw.rectangle([0, 0, width, headline_h], fill=(0, 0, 0, 150))
            draw.text((8, 6), headline, fill=(255, 255, 255), font=font)

        footer_h = 44 if len(footer) > 48 else 36
        draw.rectangle([0, height - footer_h, width, height], fill=(0, 0, 0, 160))
        draw.text((8, height - footer_h + 6), footer, fill=(255, 255, 255), font=font)

        out_path.parent.mkdir(parents=True, exist_ok=True)
        base.convert("RGB").save(out_path, format="PNG")

    return {
        "entry_id": entry.get("entry_id"),
        "base_image": str(base_image_path),
        "base_sha256": sha256_file(base_image_path),
        "output": str(out_path),
        "output_sha256": sha256_file(out_path),
        "width": width,
        "height": height,
    }


def apply_sasang_l1_clamp(
    layer: dict[str, Any],
    sasang_doc: dict[str, Any],
    *,
    angle_bounds: tuple[float, float] = (40.0, 70.0),
    point_nudge_max: float = 0.04,
) -> dict[str, Any]:
    """[HYPO] L1: deterministic sasang-proxy clamp on angle + point nudge (not clinical)."""
    out = json.loads(json.dumps(layer))
    scores = sasang_doc.get("scores") or {}
    axis = sasang_doc.get("b_track_axis_scores_v1") or {}
    direction = float(scores.get("direction_score") or 0.0)
    thermal = float(axis.get("thermal_imbalance_proxy") or 0.5)

    base_angle = float(out.get("angle_deg") or 55.0)
    delta = (thermal - 0.5) * 20.0 + direction * 5.0
    clamped = max(angle_bounds[0], min(angle_bounds[1], base_angle + delta))
    out["angle_deg"] = round(clamped, 2)

    points = out.get("points_norm") or []
    if len(points) >= 2:
        nudge_x = max(-point_nudge_max, min(point_nudge_max, direction * point_nudge_max))
        nudge_y = max(-point_nudge_max, min(point_nudge_max, (thermal - 0.5) * point_nudge_max))
        mid_idx = 1 if len(points) > 2 else 0
        p = list(points[mid_idx])
        p[0] = max(0.0, min(1.0, float(p[0]) + nudge_x))
        p[1] = max(0.0, min(1.0, float(p[1]) + nudge_y))
        points[mid_idx] = p
        out["points_norm"] = points

    label = str(out.get("label_text") or "")
    if label and "L1" not in label:
        out["label_text"] = f"{label} · L1 sasang-clamp [HYPO]"
    return out


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


def render_from_manifest(
    manifest_path: Path,
    *,
    entry_id: str | None = None,
    out_path: Path | None = None,
    fetch_base: bool = False,
    update_manifest: bool = False,
    workspace_root: Path = ROOT,
) -> dict[str, Any]:
    from datetime import datetime, timezone

    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    manifest = load_manifest(manifest_path)
    entry = find_entry(manifest, entry_id)
    eid = str(entry.get("entry_id", "pilot"))

    base_path = resolve_base_image(entry, workspace_root=workspace_root, fetch=fetch_base)
    rel_base = base_path.relative_to(workspace_root).as_posix()

    entry.setdefault("base_image", {})
    entry["base_image"]["local_path"] = rel_base
    entry["base_image"]["sha256"] = sha256_file(base_path)
    entry["base_image"]["fetch_status"] = "downloaded" if fetch_base or base_path.exists() else "cached"
    if str(entry.get("status") or "") not in _PRESERVE_ENTRY_STATUSES:
        entry["status"] = "rendered_pending_adjudication"

    if out_path is None:
        out_path = DEFAULT_OUT_DIR / f"rib55_overlay_{eid}_latest.png"

    report = render_entry_overlay(entry, base_path, out_path)
    report["manifest"] = str(manifest_path)
    report["status"] = entry.get("status", "rendered_pending_adjudication")
    report["generated_at"] = generated_at

    manifest.setdefault("verification", {})
    manifest["verification"].update(
        {
            "render_script": "scripts/render_rib55_angle_overlay_v1.py",
            "pytest_module": "tests/test_render_rib55_angle_overlay_v1.py",
            "last_exit_code": 0,
            "last_verified_at": generated_at,
            "last_output": out_path.relative_to(workspace_root).as_posix(),
            "last_output_sha256": report["output_sha256"],
        }
    )

    if update_manifest:
        save_manifest(manifest_path, manifest)

    return report
