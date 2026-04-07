#!/usr/bin/env python3
"""Showroom visual quality gate for atlas-only production mode."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple


REQUIRED_FRAMES = (
    "hero_idle_0",
    "hero_idle_1",
    "hero_attack_0",
    "hero_attack_1",
    "hero_hit_0",
)


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _extract_literal(content: str, pattern: str) -> str | None:
    m = re.search(pattern, content, flags=re.MULTILINE)
    return m.group(1) if m else None


def _check_frame_sizes(meta: Dict[str, Any], min_px: int, max_px: int) -> List[str]:
    errors: List[str] = []
    for fr in meta.get("frames", []):
        name = str(fr.get("name", ""))
        frame = fr.get("frame", {})
        w = int(frame.get("w", 0))
        h = int(frame.get("h", 0))
        if w < min_px or h < min_px:
            errors.append(f"frame too small: {name} ({w}x{h} < {min_px})")
        if w > max_px or h > max_px:
            errors.append(f"frame too large: {name} ({w}x{h} > {max_px})")
    return errors


def _check_required_frames(meta: Dict[str, Any]) -> List[str]:
    names = {str(fr.get("name", "")) for fr in meta.get("frames", [])}
    missing = [name for name in REQUIRED_FRAMES if name not in names]
    return [f"required frame missing: {name}" for name in missing]


def _check_showroom_contract(showroom_html: Path) -> List[str]:
    errors: List[str] = []
    content = showroom_html.read_text(encoding="utf-8")

    render_default = _extract_literal(
        content, r'stageState\s*=\s*\{[\s\S]*?renderMode:\s*"([^"]+)"'
    )
    if render_default != "atlas_only":
        errors.append(f"stageState.renderMode default must be atlas_only (got: {render_default})")

    fx_default = _extract_literal(
        content, r'stageState\s*=\s*\{[\s\S]*?fxPreset:\s*"([^"]+)"'
    )
    if fx_default != "CALM":
        errors.append(f"stageState.fxPreset default must be CALM (got: {fx_default})")

    if '<option value="atlas_only" selected>ATLAS_ONLY</option>' not in content:
        errors.append("renderMode select must expose atlas_only as the primary option")

    if "const allowDebugFallback = stageState.renderMode !== \"atlas_only\";" not in content:
        errors.append("fallback guard missing: allowDebugFallback contract not found")
    if 'id="trustBadge"' not in content:
        errors.append("trust badge missing: #trustBadge")
    if "function explainReasonLine(" not in content:
        errors.append("explain engine missing: explainReasonLine()")
    if "function setQuestCard(" not in content:
        errors.append("quest card missing: setQuestCard()")

    return errors


def _resolve_game_root(path: Path) -> Path:
    return path.resolve()


def run_gate(
    game_root: Path,
    pointer_name: str = "atlas_latest_browser.json",
    min_frame_px: int = 8,
    max_frame_px: int = 2048,
) -> Tuple[bool, List[str]]:
    errors: List[str] = []
    root = _resolve_game_root(game_root)
    pointer = root / pointer_name
    showroom_html = root / "public_showroom_poll.html"
    if not pointer.is_file():
        return False, [f"missing pointer: {pointer}"]
    if not showroom_html.is_file():
        return False, [f"missing showroom html: {showroom_html}"]

    ptr = _load_json(pointer)
    metadata_rel = str(ptr.get("metadata_json", "")).strip()
    atlas_webp_rel = str(ptr.get("atlas_webp", "")).strip()
    atlas_png_rel = str(ptr.get("atlas_png", "")).strip()

    if not metadata_rel:
        errors.append("pointer missing metadata_json")
    if not atlas_webp_rel and not atlas_png_rel:
        errors.append("pointer missing atlas_webp/atlas_png")

    meta_path = root / metadata_rel if metadata_rel else None
    if meta_path and not meta_path.is_file():
        errors.append(f"metadata file not found: {meta_path}")
    meta = _load_json(meta_path) if meta_path and meta_path.is_file() else {}

    if atlas_webp_rel:
        atlas_webp = root / atlas_webp_rel
        if not atlas_webp.is_file():
            errors.append(f"atlas_webp file not found: {atlas_webp}")
    if atlas_png_rel:
        atlas_png = root / atlas_png_rel
        if not atlas_png.is_file() and not atlas_webp_rel:
            errors.append(f"atlas_png file not found: {atlas_png}")

    if meta:
        if not isinstance(meta.get("frames"), list) or not meta.get("frames"):
            errors.append("metadata frames missing or empty")
        errors.extend(_check_required_frames(meta))
        errors.extend(_check_frame_sizes(meta, min_px=min_frame_px, max_px=max_frame_px))

    errors.extend(_check_showroom_contract(showroom_html))
    return (len(errors) == 0), errors


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Verify showroom visual quality contracts.")
    p.add_argument(
        "--game-root",
        default="projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp",
        help="Showroom game root directory.",
    )
    p.add_argument("--pointer-name", default="atlas_latest_browser.json")
    p.add_argument("--min-frame-px", type=int, default=8)
    p.add_argument("--max-frame-px", type=int, default=2048)
    return p


def main() -> int:
    ns = _parser().parse_args()
    ok, errors = run_gate(
        game_root=Path(ns.game_root),
        pointer_name=ns.pointer_name,
        min_frame_px=ns.min_frame_px,
        max_frame_px=ns.max_frame_px,
    )
    if ok:
        print("[quality-gate] PASS")
        return 0
    print("[quality-gate] FAIL")
    for e in errors:
        print(f"- {e}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
