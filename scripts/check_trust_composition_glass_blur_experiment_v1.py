#!/usr/bin/env python3
"""Gate: Trust Composition glass/blur experiment — internal preview + tokens.

NOT clinic LOI default. Writes reports/trust_composition_glass_blur_gate_v1_latest.json
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
TOKENS = ROOT / "reports/trust_composition_glass_blur_tokens_experiment_v1.dtcg.json"
PREVIEW = ROOT / "reports/trust_composition_glass_blur_preview_v1.html"
SEED = ROOT / "reports/design_reference_seed_glass_blur_experiment_v1.json"
OUT = ROOT / "reports/trust_composition_glass_blur_gate_v1_latest.json"

FORBIDDEN_COPY = ("환각 0%", "AI 진단", "47.5%", "완치", "100%")
REQUIRED_WEDGE = ("근거 없으면", "답하지 않습니다")
MAX_BLUR_PX = 12.0
MAX_MOTION = 0.2


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _hex_to_rgb(hex_color: str) -> tuple[float, float, float]:
    h = hex_color.lstrip("#")
    r = int(h[0:2], 16) / 255.0
    g = int(h[2:4], 16) / 255.0
    b = int(h[4:6], 16) / 255.0
    return r, g, b


def _relative_luminance(rgb: tuple[float, float, float]) -> float:
    def ch(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (ch(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(fg: str, bg: str) -> float:
    l1 = _relative_luminance(_hex_to_rgb(fg))
    l2 = _relative_luminance(_hex_to_rgb(bg))
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    errors: list[str] = []
    checks: list[dict[str, Any]] = []

    if not SEED.is_file():
        errors.append(f"missing seed: {SEED}")
    else:
        seed = json.loads(SEED.read_text(encoding="utf-8-sig"))
        seed_ok = (
            seed.get("schema") == "design_reference_seed_v1"
            and seed.get("lane_status") == "research_only"
            and seed.get("experiment_tier") == "needs_experiment"
        )
        if not seed_ok:
            errors.append("seed: research_only / needs_experiment required")
        checks.append({"kind": "seed", "ok": seed_ok})

    tokens_doc: dict[str, Any] | None = None
    if not TOKENS.is_file():
        errors.append(f"missing tokens: {TOKENS}")
    else:
        tokens_doc = json.loads(TOKENS.read_text(encoding="utf-8-sig"))
        vars_resolved = tokens_doc.get("css_variables_resolved") or {}
        blur_s = str(vars_resolved.get("--tc-glass-blur-max", ""))
        m = re.search(r"([\d.]+)", blur_s)
        blur_px = float(m.group(1)) if m else 999.0
        motion = float(vars_resolved.get("--tc-glass-motion-cap", 999))
        tok_ok = (
            tokens_doc.get("preset") == "trust-composition-glass-blur-experiment"
            and blur_px <= MAX_BLUR_PX
            and motion <= MAX_MOTION
        )
        if not tok_ok:
            errors.append(f"tokens: blur/motion cap fail blur={blur_px} motion={motion}")
        checks.append({"kind": "tokens", "ok": tok_ok, "blur_px": blur_px, "motion_cap": motion})

    preview_text = PREVIEW.read_text(encoding="utf-8") if PREVIEW.is_file() else ""
    if not preview_text:
        errors.append(f"missing preview: {PREVIEW}")
    else:
        exp_ok = 'data-experiment="glass_blur_v1"' in preview_text
        wedge_ok = all(w in preview_text for w in REQUIRED_WEDGE)
        not_clinic_default = "clinic LOI 기본 적용 금지" in preview_text
        blur_css_ok = "blur(var(--tc-glass-blur-max))" in preview_text or "blur(12px)" in preview_text
        prev_ok = exp_ok and wedge_ok and not_clinic_default and blur_css_ok
        if not prev_ok:
            errors.append("preview: experiment marker / wedge / clinic-default-ban")
        checks.append({"kind": "preview", "ok": prev_ok})

        for bad in FORBIDDEN_COPY:
            if bad in preview_text:
                errors.append(f"forbidden copy in preview: {bad}")

    if tokens_doc:
        bg = (tokens_doc.get("css_variables_resolved") or {}).get("--tc-glass-bg", "#f9f9fb")
        text = (tokens_doc.get("css_variables_resolved") or {}).get("--tc-glass-text", "#191f28")
        ratio = contrast_ratio(text, bg)
        contrast_ok = ratio >= 4.5
        if not contrast_ok:
            errors.append(f"contrast fail: {ratio:.2f} < 4.5")
        checks.append({"kind": "contrast", "ok": contrast_ok, "ratio": round(ratio, 2)})

    decision = "PASS" if not errors else "FAIL"
    doc = {
        "schema": "trust_composition_glass_blur_gate_v1",
        "generated_at_utc": _utc(),
        "ok": not errors,
        "decision": decision,
        "research_only": True,
        "send_gate": "HOLD",
        "lane_status": "research_only",
        "experiment_tier": "needs_experiment",
        "not_clinic_loi_default": True,
        "errors": errors,
        "checks": checks,
        "artifacts": {
            "seed": str(SEED.relative_to(ROOT)).replace("\\", "/"),
            "tokens": str(TOKENS.relative_to(ROOT)).replace("\\", "/"),
            "preview": str(PREVIEW.relative_to(ROOT)).replace("\\", "/"),
        },
        "reproduce": "py scripts/check_trust_composition_glass_blur_experiment_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": not errors, "decision": decision, "out": str(args.out), "errors": len(errors)}))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
