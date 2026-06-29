# -*- coding: utf-8 -*-
"""[HYPO] Deterministic Han Vocology flowchart renderer — no generative anatomy pixels.

Policy: docs/final/artifacts/anatomy_image_hallucination_control_protocol_hypo_v1_latest.md
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = frozenset({"han_vocology_flowchart_spec_v1", "han_vocology_mtd_flowchart_spec_v1"})


def load_spec(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") not in SCHEMAS:
        raise ValueError(f"unexpected spec schema: {data.get('schema')}")
    return data


def _center(box: dict[str, Any]) -> tuple[int, int]:
    return box["x"] + box["w"] // 2, box["y"] + box["h"] // 2


def _arrow_head(draw: Any, ax: int, ay: int, bx: int, by: int) -> None:
    if abs(by - ay) >= abs(bx - ax):
        if by > ay:
            draw.polygon([(bx, by - 6), (bx - 5, by - 14), (bx + 5, by - 14)], fill=(80, 80, 80))
        else:
            draw.polygon([(bx, by + 6), (bx - 5, by + 14), (bx + 5, by + 14)], fill=(80, 80, 80))
    elif bx > ax:
        draw.polygon([(bx - 6, by), (bx - 14, by - 5), (bx - 14, by + 5)], fill=(80, 80, 80))
    else:
        draw.polygon([(bx + 6, by), (bx + 14, by - 5), (bx + 14, by + 5)], fill=(80, 80, 80))


def render_flowchart(spec: dict[str, Any], out_path: Path) -> dict[str, Any]:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as exc:
        raise SystemExit("Pillow required: pip install pillow") from exc

    canvas = spec.get("canvas") or {}
    canvas_w = int(canvas.get("width", 780))
    canvas_h = int(canvas.get("height", 420))
    img = Image.new("RGB", (canvas_w, canvas_h), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("malgun.ttf", 14)
        font_title = ImageFont.truetype("malgun.ttf", 16)
        font_small = ImageFont.truetype("malgun.ttf", 11)
    except OSError:
        font = ImageFont.load_default()
        font_title = font
        font_small = font

    title = spec.get("title_ko", "flowchart")
    draw.text((20, 8), title, fill=(20, 40, 80), font=font_title)

    nodes = {n["id"]: n for n in spec["nodes"]}
    for node in spec["nodes"]:
        x, y, w, h = node["x"], node["y"], node["w"], node["h"]
        fill = tuple(node.get("fill_rgb", [240, 248, 255]))
        outline = tuple(node.get("outline_rgb", [40, 90, 140]))
        draw.rounded_rectangle((x, y, x + w, y + h), radius=8, outline=outline, width=2, fill=fill)
        lines = str(node["text"]).split("\n")
        ty = y + 10
        for line in lines:
            draw.text((x + 10, ty), line, fill=(20, 20, 20), font=font)
            ty += 18

    for edge in spec.get("edges", []):
        if isinstance(edge, list):
            a, b = edge[0], edge[1]
        else:
            a, b = edge["from"], edge["to"]
        ax, ay = _center(nodes[a])
        bx, by = _center(nodes[b])
        draw.line((ax, ay, bx, by), fill=(80, 80, 80), width=2)
        _arrow_head(draw, ax, ay, bx, by)

    footer = spec.get("footer_ko", "")
    if footer:
        draw.text((20, canvas_h - 36), footer, fill=(120, 60, 60), font=font_small)
    evidence = spec.get("evidence_note", "")
    if evidence:
        draw.text((20, canvas_h - 20), evidence, fill=(60, 60, 60), font=font_small)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, format="PNG")

    return {
        "ok": True,
        "schema": "han_vocology_flowchart_render_report_v1",
        "fig_id": spec.get("fig_id"),
        "output": out_path.as_posix(),
        "canvas": {"width": canvas_w, "height": canvas_h},
        "node_count": len(spec.get("nodes", [])),
        "edge_count": len(spec.get("edges", [])),
        "deterministic": True,
        "generative_anatomy": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Render Han Vocology flowchart (deterministic)")
    ap.add_argument("--spec", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--report-out", type=Path, default=None)
    args = ap.parse_args()

    spec = load_spec(args.spec)
    report = render_flowchart(spec, args.out)
    report["generated_at_utc"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    report["spec"] = args.spec.as_posix()

    if args.report_out:
        args.report_out.parent.mkdir(parents=True, exist_ok=True)
        args.report_out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"ok": True, "output": report["output"], "fig_id": report.get("fig_id")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
