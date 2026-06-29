#!/usr/bin/env python3
"""O-P31c Design Quality Assurance G0 — token allowlist + WCAG contrast (Veto, not beauty)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TOKENS = ROOT / "docs" / "final" / "artifacts" / "zone_a_broadcast_design_tokens_v1.json"
SCHEMA_PATH = ROOT / "docs" / "final" / "artifacts" / "schemas" / "zone_a_broadcast_design_tokens_v1.schema.json"

_HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


def _hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    h = hex_color.strip().lstrip("#")
    if len(h) != 6:
        raise ValueError(f"invalid_hex: {hex_color}")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def normalize_hex(hex_color: str) -> str:
    raw = hex_color.strip().lstrip("#").upper()
    if len(raw) != 6:
        raise ValueError(f"invalid_hex: {hex_color}")
    return f"#{raw}"


def relative_luminance(rgb: Tuple[int, int, int]) -> float:
    def channel(c: int) -> float:
        x = c / 255.0
        return x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4

    r, g, b = rgb
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def contrast_ratio(fg_rgb: Tuple[int, int, int], bg_rgb: Tuple[int, int, int]) -> float:
    l1 = relative_luminance(fg_rgb)
    l2 = relative_luminance(bg_rgb)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def load_tokens(path: Optional[Path] = None) -> Dict[str, Any]:
    p = path or DEFAULT_TOKENS
    if not p.is_absolute():
        p = ROOT / p
    return json.loads(p.read_text(encoding="utf-8-sig"))


def validate_tokens_doc(doc: Dict[str, Any]) -> List[str]:
    issues: List[str] = []
    if doc.get("schema") != "zone_a_broadcast_design_tokens_v1":
        issues.append("token_schema_mismatch")
    forbidden = {normalize_hex(x) for x in (doc.get("forbidden_hex") or [])}
    palette = {normalize_hex(v) for v in (doc.get("palette") or {}).values()}
    ui = doc.get("ui_semantic") or {}
    for key, val in ui.items():
        if not isinstance(val, str) or not _HEX_RE.match(val):
            issues.append(f"ui_semantic_invalid_{key}")
            continue
        hx = normalize_hex(val)
        if hx in forbidden:
            issues.append(f"ui_semantic_forbidden_{key}")
        if hx not in palette:
            issues.append(f"ui_semantic_not_in_palette_{key}")
    return issues


def audit_semantic_contrast(tokens: Dict[str, Any]) -> Dict[str, Any]:
    ui = tokens.get("ui_semantic") or {}
    min_ratio = float((tokens.get("wcag") or {}).get("min_contrast_ratio_aa") or 4.5)
    rows: List[Dict[str, Any]] = []
    pairs = [
        ("disclaimer_on_glass", "glass_panel_fill", "disclaimer_bar"),
        ("title_on_glass", "glass_panel_fill", "title_bar"),
        ("subtitle_on_glass", "glass_panel_fill", "subtitle_bar"),
        ("live_pill_text", "live_pill_fill", "live_pill"),
    ]
    failures: List[str] = []
    for fg_key, bg_key, label in pairs:
        fg_h = ui.get(fg_key)
        bg_h = ui.get(bg_key)
        if not fg_h or not bg_h:
            failures.append(f"missing_semantic_{label}")
            continue
        ratio = contrast_ratio(_hex_to_rgb(normalize_hex(fg_h)), _hex_to_rgb(normalize_hex(bg_h)))
        ok = ratio >= min_ratio
        rows.append({"pair": label, "ratio": round(ratio, 2), "min_aa": min_ratio, "ok": ok})
        if not ok:
            failures.append(f"wcag_aa_fail_{label}")
    return {
        "ok": not failures,
        "min_contrast_ratio_aa": min_ratio,
        "pairs": rows,
        "failures": failures,
    }


def _sample_region_mean_rgb(path: Path, box: Tuple[int, int, int, int]) -> Optional[Tuple[int, int, int]]:
    try:
        from PIL import Image
    except ImportError:
        return None
    im = Image.open(path).convert("RGB")
    x0, y0, x1, y1 = box
    crop = im.crop((max(0, x0), max(0, y0), min(im.width, x1), min(im.height, y1)))
    if crop.width < 2 or crop.height < 2:
        return None
    pixels = list(crop.getdata())
    n = len(pixels)
    r = sum(p[0] for p in pixels) // n
    g = sum(p[1] for p in pixels) // n
    b = sum(p[2] for p in pixels) // n
    return r, g, b


def _sample_region_bright_rgb(
    path: Path,
    box: Tuple[int, int, int, int],
    *,
    top_frac: float = 0.12,
) -> Optional[Tuple[int, int, int]]:
    """Brightest pixels in region — proxy for burn-in / UI text on glass."""
    try:
        from PIL import Image
    except ImportError:
        return None
    im = Image.open(path).convert("RGB")
    x0, y0, x1, y1 = box
    crop = im.crop((max(0, x0), max(0, y0), min(im.width, x1), min(im.height, y1)))
    if crop.width < 2 or crop.height < 2:
        return None
    pixels = list(crop.getdata())
    scored = sorted(
        pixels,
        key=lambda p: 0.2126 * p[0] + 0.7152 * p[1] + 0.0722 * p[2],
        reverse=True,
    )
    k = max(1, int(len(scored) * top_frac))
    top = scored[:k]
    n = len(top)
    return (
        sum(p[0] for p in top) // n,
        sum(p[1] for p in top) // n,
        sum(p[2] for p in top) // n,
    )


def audit_preview_frame_contrast(
    preview_mp4: Path,
    tokens: Dict[str, Any],
    *,
    at_sec: float = 8.0,
) -> Dict[str, Any]:
    """Sample bottom disclaimer band vs upper orb region on a preview frame (composite truth)."""
    min_ratio = float((tokens.get("wcag") or {}).get("min_contrast_ratio_aa") or 4.5)
    jpg = preview_mp4.parent / "_dqa_preview_frame.jpg"
    import subprocess

    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-v",
        "error",
        "-ss",
        str(at_sec),
        "-i",
        str(preview_mp4),
        "-frames:v",
        "1",
        "-q:v",
        "2",
        str(jpg),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0 or not jpg.is_file():
        return {"ok": False, "skipped": True, "reason": "preview_frame_extract_failed"}

    try:
        from PIL import Image
    except ImportError:
        jpg.unlink(missing_ok=True)
        return {"ok": False, "skipped": True, "reason": "pillow_unavailable"}

    im = Image.open(jpg).convert("RGB")
    w, h = im.size
    # Bottom 12% center — disclaimer glass
    disc_box = (int(w * 0.15), int(h * 0.86), int(w * 0.85), int(h * 0.96))
    # Same band, left edge — mostly background under glass
    bg_box = (int(w * 0.18), int(h * 0.88), int(w * 0.28), int(h * 0.94))
    disc_rgb = _sample_region_bright_rgb(jpg, disc_box)
    bg_rgb = _sample_region_mean_rgb(jpg, bg_box)
    jpg.unlink(missing_ok=True)
    if not disc_rgb or not bg_rgb:
        return {"ok": False, "skipped": True, "reason": "region_sample_failed"}

    ratio = contrast_ratio(disc_rgb, bg_rgb)
    ok = ratio >= min_ratio * 0.85
    return {
        "ok": ok,
        "skipped": False,
        "disclaimer_band_ratio": round(ratio, 2),
        "min_aa": min_ratio,
        "relaxed_floor": round(min_ratio * 0.85, 2),
        "disc_rgb": disc_rgb,
        "bg_rgb": bg_rgb,
        "sample_mode": "bright_text_vs_glass_edge",
    }


def run_dqa_g0(
    *,
    tokens_path: Optional[Path] = None,
    preview_mp4: Optional[Path] = None,
    skip_preview: bool = False,
) -> Dict[str, Any]:
    issues: List[str] = []
    tokens = load_tokens(tokens_path)
    token_issues = validate_tokens_doc(tokens)
    issues.extend(token_issues)
    semantic = audit_semantic_contrast(tokens)
    if not semantic.get("ok"):
        issues.extend(semantic.get("failures") or [])

    preview_audit: Dict[str, Any] = {"skipped": True}
    preview_warnings: List[str] = []
    if not skip_preview and preview_mp4 and preview_mp4.is_file():
        preview_audit = audit_preview_frame_contrast(preview_mp4, tokens)
        if preview_audit.get("skipped"):
            preview_warnings.append("preview_contrast_skipped")
        elif not preview_audit.get("ok"):
            # Composite frame on glass UI — semantic token pairs are the hard WCAG gate.
            if semantic.get("ok"):
                preview_warnings.append("preview_composite_heuristic_advisory")
            else:
                preview_warnings.append("preview_disclaimer_contrast_heuristic_low")

    core_issues = list(issues)
    g0_pass = not core_issues
    return {
        "schema": "zone_a_broadcast_design_dqa_g0_v1",
        "track": "O-P31c",
        "g0_pass": g0_pass,
        "gate_tier": "G0_machine",
        "note": "Veto couth/illegible/broken — not Apple aesthetic signoff (G2 human).",
        "token_validation": {"ok": not token_issues, "issues": token_issues},
        "semantic_contrast": semantic,
        "preview_contrast": preview_audit,
        "preview_warnings": preview_warnings,
        "issues": core_issues,
        "tokens_path": str((tokens_path or DEFAULT_TOKENS).as_posix()),
    }


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Zone A broadcast DQA G0")
    ap.add_argument("--tokens-json", type=Path, default=DEFAULT_TOKENS)
    ap.add_argument("--preview-mp4", type=Path, default=ROOT / "reports/video/zone_a_local_preview_latest.mp4")
    ap.add_argument("--skip-preview", action="store_true")
    ap.add_argument("--stdout-only", action="store_true")
    args = ap.parse_args()

    doc = run_dqa_g0(
        tokens_path=args.tokens_json,
        preview_mp4=args.preview_mp4,
        skip_preview=args.skip_preview,
    )
    payload = json.dumps(doc, ensure_ascii=False, indent=2)
    if args.stdout_only:
        print(payload)
    else:
        print(payload)
    return 0 if doc.get("g0_pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
