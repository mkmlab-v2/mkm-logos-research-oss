#!/usr/bin/env python3
"""PersonaDiary Android design tokens v1 — load SSOT and validate CSS alignment."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "docs/final/schemas/personadiary_android_design_tokens_v1.schema.json"
DEFAULT_SSOT = ROOT / "docs/final/artifacts/personadiary_android_design_tokens_v1_latest.json"
DEFAULT_CSS = ROOT / "projects/no1kmedi/src/app/globals.css"
DEFAULT_MAIN_ACTIVITY = (
    ROOT
    / "projects/no1kmedi/personadiary-native-hypo-v1/android/app/src/main/java/com/mkmlife/personadiary/hypo/MainActivity.java"
)
DEFAULT_STYLES = (
    ROOT / "projects/no1kmedi/personadiary-native-hypo-v1/android/app/src/main/res/values/styles.xml"
)


def load_ssot(path: str | Path | None = None) -> dict:
    p = Path(path) if path else DEFAULT_SSOT
    return json.loads(p.read_text(encoding="utf-8-sig"))


def _css_var_pattern(name: str, value: str) -> re.Pattern[str]:
    escaped = re.escape(value)
    return re.compile(rf"{re.escape(name)}\s*:\s*{escaped}", re.IGNORECASE)


def validate_ssot_paths(doc: dict) -> list[str]:
    errors: list[str] = []
    css_rel = doc.get("css_ssot")
    if css_rel and not (ROOT / css_rel).is_file():
        errors.append(f"missing css_ssot:{css_rel}")
    native_rel = doc.get("native_shell_ssot")
    if native_rel and not (ROOT / native_rel).is_dir():
        errors.append(f"missing native_shell_ssot:{native_rel}")
    return errors


def validate_css_alignment(doc: dict, css_text: str) -> list[str]:
    errors: list[str] = []
    marker = doc.get("css_marker_comment") or ""
    if marker and marker not in css_text:
        errors.append(f"css_marker_missing:{marker}")

    for var_name, var_value in (doc.get("css_variables") or {}).items():
        if not _css_var_pattern(var_name, var_value).search(css_text):
            errors.append(f"css_var_drift:{var_name}={var_value}")

    palette = doc.get("palette") or {}
    for key, hex_val in palette.items():
        if hex_val.lower() not in css_text.lower():
            errors.append(f"palette_hex_missing:{key}={hex_val}")

    touch_min = int((doc.get("m3_inspired") or {}).get("touch_target_min_px") or 48)
    touch_hits = len(re.findall(rf"min-height:\s*{touch_min}px", css_text))
    if touch_hits < 3:
        errors.append(f"touch_target_min_px:{touch_min} (found {touch_hits} min-height hits, need >=3)")

    fab_radius = int((doc.get("m3_inspired") or {}).get("shape_radius_px", {}).get("fab") or 16)
    fab_block = re.search(r"\.pd-ops-fab\s*\{[^}]+\}", css_text, re.DOTALL)
    fab_ok = False
    if fab_block:
        block = fab_block.group(0)
        fab_ok = (
            f"border-radius: {fab_radius}px" in block
            or f"border-radius: var(--pd-android-fab-radius, {fab_radius}px)" in block
        )
    if not fab_ok:
        errors.append(f"fab_radius_missing:{fab_radius}px")

    layout = doc.get("layout") or {}
    max_w = layout.get("content_max_width_rem")
    if max_w is not None and f"max-width: {max_w}rem" not in css_text:
        errors.append(f"content_max_width_rem:{max_w}")

    fab_reserve = layout.get("fab_bottom_reserve_rem")
    if fab_reserve is not None and f"{fab_reserve}rem + var(--pd-safe-bottom" not in css_text:
        errors.append(f"fab_bottom_reserve_rem:{fab_reserve}")

    for selector in doc.get("css_selectors_required") or []:
        if selector not in css_text:
            errors.append(f"css_selector_missing:{selector}")

    motion = doc.get("motion") or {}
    if motion.get("prefers_reduced_motion_respected") and "@media (prefers-reduced-motion: reduce)" not in css_text:
        errors.append("prefers_reduced_motion_block_missing")

    return errors


def validate_native_edge_to_edge(doc: dict) -> list[str]:
    errors: list[str] = []
    edge = doc.get("edge_to_edge") or {}
    if not edge:
        return ["edge_to_edge_missing"]

    main_rel = edge.get("native_main_activity") or ""
    main_path = ROOT / main_rel if main_rel else DEFAULT_MAIN_ACTIVITY
    if not main_path.is_file():
        errors.append(f"native_main_activity_missing:{main_rel}")
    else:
        main_src = main_path.read_text(encoding="utf-8")
        for needle in (
            "injectSafeAreaCss",
            "setProperty('--safe-area-inset-top'",
            "setBackgroundColor",
            "shortEdges",
        ):
            if needle == "shortEdges":
                continue
            if needle not in main_src:
                errors.append(f"native_main_missing:{needle}")

    styles_path = DEFAULT_STYLES
    if styles_path.is_file():
        styles_xml = styles_path.read_text(encoding="utf-8")
        if edge.get("styles_cutout_mode", "shortEdges") not in styles_xml:
            errors.append("styles_cutout_mode_missing:shortEdges")
        if "enforceNavigationBarContrast" not in styles_xml and "navigationBarContrastEnforced" not in styles_xml:
            errors.append("styles_navigation_bar_contrast_missing")
    else:
        errors.append(f"styles_xml_missing:{styles_path.relative_to(ROOT)}")

    css_classes = edge.get("css_root_classes") or []
    css_file = ROOT / doc.get("css_ssot", "")
    css_text = css_file.read_text(encoding="utf-8") if css_file.is_file() else ""
    for cls in css_classes:
        token = f".{cls}" if not cls.startswith(".") else cls
        if token not in css_text and cls not in css_text:
            errors.append(f"css_root_class_missing:{cls}")

    webview_bg = (edge.get("webview_background") or "").lower()
    if webview_bg and css_text and webview_bg not in css_text.lower():
        errors.append(f"webview_background_missing:{webview_bg}")

    return errors


def validate_figma_paths(doc: dict) -> list[str]:
    errors: list[str] = []
    figma = doc.get("figma") or {}
    if not figma:
        return errors
    for key in ("token_map", "design_ssot"):
        rel = figma.get(key)
        if rel and not (ROOT / rel).is_file():
            errors.append(f"figma_path_missing:{key}={rel}")
    return errors


def validate_ssot(doc: dict, css_path: Path | None = None) -> list[str]:
    errors = validate_ssot_paths(doc)
    css_file = css_path or (ROOT / doc.get("css_ssot", ""))
    if css_file.is_file():
        errors.extend(validate_css_alignment(doc, css_file.read_text(encoding="utf-8")))
    elif doc.get("css_ssot"):
        errors.append(f"missing_css_file:{doc['css_ssot']}")
    errors.extend(validate_native_edge_to_edge(doc))
    errors.extend(validate_figma_paths(doc))
    return errors
