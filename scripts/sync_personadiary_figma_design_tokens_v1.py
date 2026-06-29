#!/usr/bin/env python3
"""Sync + validate PersonaDiary Figma token map against Android design tokens SSOT."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from personadiary_android_design_tokens_v1 import (  # noqa: E402
    DEFAULT_CSS,
    DEFAULT_SSOT,
    load_ssot,
    validate_ssot,
)

MAP_PATH = ROOT / "docs/final/artifacts/personadiary_figma_token_map_v1.json"
FIGMA_SSOT = ROOT / "docs/final/artifacts/personadiary_figma_design_ssot_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/personadiary_figma_design_sync_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _figma_token() -> str | None:
    for key in ("FIGMA_ACCESS_TOKEN", "MKM_FIGMA_ACCESS_TOKEN"):
        val = os.environ.get(key, "").strip()
        if val:
            return val
    env_path = ROOT / ".env"
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("FIGMA_ACCESS_TOKEN=") or line.startswith("MKM_FIGMA_ACCESS_TOKEN="):
                return line.split("=", 1)[1].strip().strip('"')
    return None


def _hex_norm(value: str) -> str:
    v = value.strip().lower()
    if not v.startswith("#"):
        return v
    return v


def _m3_lookup(doc: dict, key: str):
    if "." in key:
        head, tail = key.split(".", 1)
        return (doc.get("m3_inspired") or {}).get(head, {}).get(tail)
    return (doc.get("m3_inspired") or {}).get(key)


def validate_map_against_android(map_doc: dict, android_doc: dict) -> list[str]:
    errors: list[str] = []
    palette = android_doc.get("palette") or {}
    layout = android_doc.get("layout") or {}
    spacing = (android_doc.get("m3_inspired") or {}).get("spacing_dp") or []

    for row in map_doc.get("variables") or []:
        figma_name = row.get("figma_name")
        expected = str(row.get("value", ""))
        pal_key = row.get("android_palette_key")
        if pal_key:
            actual = str(palette.get(pal_key, ""))
            if _hex_norm(actual) != _hex_norm(expected):
                errors.append(f"palette_mismatch:{figma_name}:{expected}!={actual}")

        m3_key = row.get("android_m3_key")
        if m3_key:
            if m3_key == "spacing_dp":
                idx = int(row.get("android_m3_index", -1))
                if idx < 0 or idx >= len(spacing) or str(spacing[idx]) != expected:
                    errors.append(f"spacing_mismatch:{figma_name}")
            elif m3_key == "touch_target_min_px":
                if str((android_doc.get("m3_inspired") or {}).get("touch_target_min_px")) != expected.replace("px", ""):
                    errors.append(f"touch_mismatch:{figma_name}")
            else:
                actual = _m3_lookup(android_doc, m3_key.replace("shape_radius_px.", "shape_radius_px."))
                if m3_key.startswith("shape_radius_px."):
                    sub = m3_key.split(".", 1)[1]
                    actual = (android_doc.get("m3_inspired") or {}).get("shape_radius_px", {}).get(sub)
                if str(actual) != expected.replace("px", ""):
                    errors.append(f"m3_mismatch:{figma_name}:{expected}!={actual}")

        layout_key = row.get("android_layout_key")
        if layout_key:
            actual = layout.get(layout_key)
            if layout_key == "content_max_width_rem":
                if str(int(float(actual) * 16)) != expected:
                    errors.append(f"layout_mismatch:{figma_name}")
            elif str(actual) != expected:
                errors.append(f"layout_mismatch:{figma_name}")

        css_var = row.get("css_var")
        if css_var and pal_key:
            css_expected = (android_doc.get("css_variables") or {}).get(css_var)
            if css_expected and _hex_norm(css_expected) != _hex_norm(expected):
                errors.append(f"css_var_map_mismatch:{css_var}")

    if map_doc.get("figma_file_key") != (json.loads(FIGMA_SSOT.read_text(encoding="utf-8-sig")).get("figma_file_key")):
        errors.append("figma_file_key_drift_vs_design_ssot")
    return errors


def fetch_figma_variable_map(file_key: str, token: str) -> tuple[dict[str, str] | None, str | None]:
    url = f"https://api.figma.com/v1/files/{file_key}/variables/local"
    req = urllib.request.Request(url, headers={"X-Figma-Token": token})
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return None, f"figma_api_http_{exc.code}"
    except Exception as exc:  # noqa: BLE001
        return None, f"figma_api_error:{type(exc).__name__}"

    meta = payload.get("meta") or {}
    variables = meta.get("variables") or {}
    out: dict[str, str] = {}
    for _vid, var in variables.items():
        name = var.get("name")
        if not name:
            continue
        values = var.get("valuesByMode") or {}
        if not values:
            continue
        raw = next(iter(values.values()))
        if isinstance(raw, dict) and {"r", "g", "b"} <= set(raw.keys()):
            r = int(round(float(raw["r"]) * 255))
            g = int(round(float(raw["g"]) * 255))
            b = int(round(float(raw["b"]) * 255))
            out[name] = f"#{r:02x}{g:02x}{b:02x}"
        else:
            out[name] = str(raw)
    return out, None


def validate_figma_live(map_doc: dict, live: dict[str, str]) -> list[str]:
    errors: list[str] = []
    for row in map_doc.get("variables") or []:
        name = row.get("figma_name")
        if not name:
            continue
        if name not in live:
            errors.append(f"figma_live_missing:{name}")
            continue
        expected = str(row.get("value", ""))
        actual = live[name]
        if expected.startswith("#"):
            if _hex_norm(actual) != _hex_norm(expected):
                errors.append(f"figma_live_drift:{name}")
        elif actual != expected and actual != expected.replace("px", ""):
            errors.append(f"figma_live_drift:{name}")
    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--map-json", type=Path, default=MAP_PATH)
    ap.add_argument("--android-json", type=Path, default=DEFAULT_SSOT)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--fetch-figma", action="store_true")
    ap.add_argument("--require-figma-api", action="store_true")
    args = ap.parse_args()

    errors: list[str] = []
    map_doc = json.loads(args.map_json.read_text(encoding="utf-8-sig"))
    if map_doc.get("schema") != "personadiary_figma_token_map_v1":
        errors.append("map_schema_mismatch")

    android_doc = load_ssot(args.android_json)
    errors.extend(validate_map_against_android(map_doc, android_doc))
    errors.extend(validate_ssot(android_doc, css_path=DEFAULT_CSS))

    figma_live: dict[str, str] | None = None
    figma_api_status: str | None = None
    if args.fetch_figma or args.require_figma_api:
        token = _figma_token()
        file_key = map_doc.get("figma_file_key")
        if not token:
            figma_api_status = "token_missing"
            if args.require_figma_api:
                errors.append("figma_token_missing")
        elif not file_key:
            errors.append("figma_file_key_missing")
        else:
            figma_live, figma_api_status = fetch_figma_variable_map(str(file_key), token)
            if figma_live is not None:
                errors.extend(validate_figma_live(map_doc, figma_live))
            elif args.require_figma_api:
                errors.append(figma_api_status or "figma_api_failed")

    ok = len(errors) == 0
    report = {
        "schema": "personadiary_figma_design_sync_v1",
        "generated_at_utc": _utc_now(),
        "ok": ok,
        "map_json": str(args.map_json.relative_to(ROOT)),
        "android_tokens_json": str(args.android_json.relative_to(ROOT)),
        "figma_file_key": map_doc.get("figma_file_key"),
        "figma_file_url": map_doc.get("figma_file_url"),
        "figma_api_status": figma_api_status,
        "figma_live_variable_count": len(figma_live or {}),
        "errors": errors,
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_json}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
