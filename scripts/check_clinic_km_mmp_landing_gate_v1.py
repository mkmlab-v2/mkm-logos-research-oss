#!/usr/bin/env python3
"""Gate: clinic LOI landing — DTCG tokens v2 · copy · HTML preview · contrast.

Writes reports/clinic_km_mmp_landing_gate_v1_latest.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TOKENS_V2 = ROOT / "reports/clinic_km_mmp_landing_tokens_v2.dtcg.json"
PREVIEW_HTML = ROOT / "reports/clinic_km_mmp_loi_preview_v1.html"
COPY_MD = ROOT / "reports/clinic_km_mmp_landing_copy_v1.md"
PRESELL_TXT = ROOT / "reports/clinic_km_mmp_loi_kakao_presell_v1.txt"
DRAFT_TXT = ROOT / "reports/clinic_km_mmp_loi_kakao_draft_v1.txt"
SEED_EXAMPLE = ROOT / "reports/design_reference_seed_clinic_loi_v1.example.json"
OUT = ROOT / "reports/clinic_km_mmp_landing_gate_v1_latest.json"

FORBIDDEN_COPY = (
    "환각 0%",
    "환각0%",
    "AI 진단",
    "47.5%",
    "20배",
    "완치",
    "100%",
    "무조건",
)

REQUIRED_WEDGE_FRAGMENTS = (
    "근거 없으면",
    "답하지 않습니다",
)

REQUIRED_CSS_VARS = (
    "--clinic-loi-bg",
    "--clinic-loi-accent",
    "--clinic-loi-hold",
    "--clinic-loi-hold-bg",
)

CONTRAST_PAIRS = (
    ("#191f28", "#f9f9fb", 4.5, "text on bg"),
    ("#4e5968", "#ffffff", 4.5, "secondary on surface"),
    ("#3d9b84", "#ffffff", 3.0, "accent on white (large text)"),
)


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _hex_to_rgb(hex_color: str) -> tuple[float, float, float]:
    h = hex_color.lstrip("#")
    if len(h) != 6:
        raise ValueError(hex_color)
    r = int(h[0:2], 16) / 255.0
    g = int(h[2:4], 16) / 255.0
    b = int(h[4:6], 16) / 255.0
    return r, g, b


def _relative_luminance(rgb: tuple[float, float, float]) -> float:
    r, g, b = (_relative_channel(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _relative_channel(c: float) -> float:
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def contrast_ratio(fg: str, bg: str) -> float:
    l1 = _relative_luminance(_hex_to_rgb(fg))
    l2 = _relative_luminance(_hex_to_rgb(bg))
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _check_tokens_v2(errors: list[str], checks: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not TOKENS_V2.is_file():
        errors.append(f"missing tokens: {TOKENS_V2}")
        checks.append({"kind": "tokens_v2", "ok": False})
        return None
    doc = _load_json(TOKENS_V2)
    ok = True
    if doc.get("schema") != "clinic_km_mmp_landing_tokens_v2":
        errors.append("tokens_v2: schema mismatch")
        ok = False
    preset = doc.get("preset")
    layers = doc.get(preset) or doc.get("clinic-loi-trust-light")
    if not isinstance(layers, dict):
        errors.append("tokens_v2: missing preset layers")
        ok = False
    else:
        for layer in ("primitive", "semantic", "component"):
            if layer not in layers:
                errors.append(f"tokens_v2: missing layer {layer}")
                ok = False
    resolved = doc.get("css_variables_resolved") or {}
    if resolved.get("--clinic-loi-bg") != "#f9f9fb":
        errors.append("tokens_v2: bg must be #f9f9fb for 70s readability")
        ok = False
    checks.append({"kind": "tokens_v2", "path": str(TOKENS_V2), "ok": ok})
    return doc if ok else doc


def _scan_copy_files(errors: list[str], checks: list[dict[str, Any]]) -> None:
    paths = [COPY_MD, PRESELL_TXT, DRAFT_TXT, PREVIEW_HTML]
    for path in paths:
        if not path.is_file():
            errors.append(f"missing copy artifact: {path}")
            checks.append({"kind": "copy_file", "path": str(path), "ok": False})
            continue
        text = path.read_text(encoding="utf-8")
        file_ok = True
        hits: list[str] = []
        for phrase in FORBIDDEN_COPY:
            for line in text.splitlines():
                if phrase not in line:
                    continue
                if any(m in line for m in ("금지", "FORBIDDEN", "forbidden", "표현 없음", "주장 금지")):
                    continue
                hits.append(phrase)
                file_ok = False
                break
        if path == PREVIEW_HTML:
            for frag in REQUIRED_WEDGE_FRAGMENTS:
                if frag not in text:
                    errors.append(f"preview: missing wedge fragment {frag!r}")
                    file_ok = False
            for var in REQUIRED_CSS_VARS:
                if var not in text:
                    errors.append(f"preview: missing css var {var}")
                    file_ok = False
        if hits:
            errors.append(f"{path.name}: forbidden copy {hits}")
        checks.append(
            {
                "kind": "copy_scan",
                "path": str(path),
                "ok": file_ok,
                "forbidden_hits": hits,
            }
        )


def _check_contrast(errors: list[str], checks: list[dict[str, Any]]) -> None:
    for fg, bg, min_ratio, label in CONTRAST_PAIRS:
        ratio = contrast_ratio(fg, bg)
        ok = ratio >= min_ratio
        checks.append(
            {
                "kind": "contrast",
                "label": label,
                "fg": fg,
                "bg": bg,
                "ratio": round(ratio, 2),
                "min_ratio": min_ratio,
                "ok": ok,
            }
        )
        if not ok:
            errors.append(f"contrast fail {label}: {ratio:.2f} < {min_ratio}")


def _check_seed_example(errors: list[str], checks: list[dict[str, Any]]) -> None:
    if not SEED_EXAMPLE.is_file():
        checks.append({"kind": "seed_example", "ok": False, "optional": True})
        return
    doc = _load_json(SEED_EXAMPLE)
    ok = doc.get("schema") == "design_reference_seed_v1"
    if not ok:
        errors.append("seed example: schema mismatch")
    checks.append({"kind": "seed_example", "path": str(SEED_EXAMPLE), "ok": ok})


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    errors: list[str] = []
    checks: list[dict[str, Any]] = []

    tokens = _check_tokens_v2(errors, checks)
    _scan_copy_files(errors, checks)
    _check_contrast(errors, checks)
    _check_seed_example(errors, checks)

    ok = not errors
    doc = {
        "schema": "clinic_km_mmp_landing_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "ok": ok,
        "decision": "PASS" if ok else "FAIL",
        "lane_status": "frozen_deferred",
        "send_gate": "HOLD",
        "ready_for_external_send": False,
        "research_only": True,
        "track": "B",
        "artifacts": {
            "tokens_v2": str(TOKENS_V2.relative_to(ROOT)).replace("\\", "/"),
            "preview_html": str(PREVIEW_HTML.relative_to(ROOT)).replace("\\", "/"),
            "copy_md": str(COPY_MD.relative_to(ROOT)).replace("\\", "/"),
        },
        "tokens_preset": (tokens or {}).get("preset"),
        "errors": errors,
        "checks": checks,
        "reproduce": "py scripts/check_clinic_km_mmp_landing_gate_v1.py",
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "decision": doc["decision"], "out": str(args.out), "errors": len(errors)}))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
