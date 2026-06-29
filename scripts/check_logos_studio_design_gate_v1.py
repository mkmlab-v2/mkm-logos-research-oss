#!/usr/bin/env python3
"""Gate: Logos Research Studio — token SSOT + Playwright visual smoke [HYPO].

Surface: logos.jema-ai.com / projects/no1kmedi logos-research routes.
Writes reports/logos_studio_design_gate_v1_latest.json
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GLOBALS_CSS = ROOT / "projects/no1kmedi/src/app/globals.css"
COPY_TS = ROOT / "projects/no1kmedi/src/content/logosResearchCopy.ts"
STUDIO_CLIENT = ROOT / "projects/no1kmedi/src/components/logos-research/LogosResearchStudioClient.tsx"
SMOKE_SCRIPT = ROOT / "projects/no1kmedi/scripts/smoke-logos-research-studio-mindmap-playwright-v1.mjs"
SMOKE_REPORT = ROOT / "reports/logos_studio_mindmap_playwright_smoke_v1_latest.json"
OUT = ROOT / "reports/logos_studio_design_gate_v1_latest.json"

REQUIRED_CSS_MARKERS = (
    ".logos-research-page {",
    "--lr-bg:",
    "--lr-accent:",
    ".logos-research-page .lr-studio-citation-sidecar",
    ".logos-research-page.logos-research-studio-theme--scriptorium .mkm-trust-canvas",
    ".logos-research-page.logos-research-studio-theme--scriptorium .mkm-trust-canvas-citation-dock",
    ".logos-research-page.logos-research-studio-theme--scriptorium .mkm-thinking-timeline-step",
    "var(--space-lg)",
    "var(--radius-lg)",
    ".lr-studio-omni-entry",
    "data-logos-studio-phase",
)

REQUIRED_TS_MARKERS = (
    "lr-studio-audience-modes",
    "lr-studio-pastoral-disclaimer",
    "LogosCanvasStudioLayout",
    "LogosStudioOmniEntry",
    "resolveInitialStudioPhase",
    "data-logos-studio-phase",
)

FORBIDDEN_COPY = (
    "47.5%",
    "환각 0%",
    "Track A",
    "실매매",
    "투자 권유",
)


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}


def _check_css_tokens(css: str) -> tuple[bool, list[str]]:
    missing = [m for m in REQUIRED_CSS_MARKERS if m not in css]
    return len(missing) == 0, missing


def _check_markers(text: str, markers: tuple[str, ...]) -> tuple[bool, list[str]]:
    missing = [m for m in markers if m not in text]
    return len(missing) == 0, missing


def _check_copy(copy_text: str) -> tuple[bool, list[str]]:
    hits = [frag for frag in FORBIDDEN_COPY if frag in copy_text]
    return len(hits) == 0, hits


def _run_playwright_smoke(base: str) -> tuple[int, dict[str, Any]]:
    env = {
        **dict(**__import__("os").environ),
        "LOGOS_STUDIO_SMOKE_BASE": base,
        "LOGOS_STUDIO_SMOKE_EXPECT_CANVAS": "1",
    }
    proc = subprocess.run(
        ["node", str(SMOKE_SCRIPT)],
        cwd=str(ROOT / "projects" / "no1kmedi"),
        capture_output=True,
        text=True,
        check=False,
        timeout=240,
        env=env,
    )
    doc = _read_json(SMOKE_REPORT)
    if not doc and proc.stdout.strip():
        try:
            doc = json.loads(proc.stdout.strip().splitlines()[-1])
        except json.JSONDecodeError:
            doc = {}
    return proc.returncode, doc


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-playwright-smoke", action="store_true", help="Run Playwright smoke before gate read")
    ap.add_argument("--smoke-base", default="https://logos.jema-ai.com")
    ap.add_argument("--output-json", type=Path, default=OUT)
    args = ap.parse_args(argv)

    smoke_exit = 0
    smoke_doc: dict[str, Any] = _read_json(SMOKE_REPORT)
    if args.run_playwright_smoke:
        smoke_exit, smoke_doc = _run_playwright_smoke(args.smoke_base.rstrip("/"))

    css_text = GLOBALS_CSS.read_text(encoding="utf-8") if GLOBALS_CSS.is_file() else ""
    copy_text = COPY_TS.read_text(encoding="utf-8") if COPY_TS.is_file() else ""
    ts_text = STUDIO_CLIENT.read_text(encoding="utf-8") if STUDIO_CLIENT.is_file() else ""
    css_ok, css_missing = _check_css_tokens(css_text)
    ts_ok, ts_missing = _check_markers(ts_text, REQUIRED_TS_MARKERS)
    copy_ok, copy_hits = _check_copy(copy_text)
    smoke_ok = smoke_doc.get("ok") is True and smoke_doc.get("schema") == "logos_studio_mindmap_playwright_smoke_v1"
    checks_count = len(smoke_doc.get("checks") or [])

    if args.run_playwright_smoke:
        ok = css_ok and ts_ok and copy_ok and smoke_ok and smoke_exit == 0
    else:
        ok = css_ok and ts_ok and copy_ok

    out = {
        "schema": "logos_studio_design_gate_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "surface": "logos.jema-ai.com/logos-research/studio",
        "ok": ok,
        "checks": {
            "css_token_ssot": css_ok,
            "studio_layout_ssot": ts_ok,
            "public_copy_guard": copy_ok,
            "playwright_smoke_ok": smoke_ok,
            "playwright_checks_count": checks_count,
        },
        "css_missing_markers": css_missing,
        "layout_missing_markers": ts_missing,
        "copy_forbidden_hits": copy_hits,
        "design_reference": {
            "token_block": "projects/no1kmedi/src/app/globals.css (.logos-research-page)",
            "pipeline": "MKM_TRUST_COMPOSITION_DESIGN_PIPELINE_V1.md",
            "manifesto": "MKM_DESIGN_MANIFESTO_V1.md (Silent Majesty · 8pt via --space-*)",
        },
        "smoke_artifact": str(SMOKE_REPORT),
        "smoke_summary": {
            "base": smoke_doc.get("base"),
            "checks": checks_count,
            "reproduce": smoke_doc.get("reproduce"),
        },
        "public_facing_contract": {
            "tag": "[NON_GATING]",
            "track_a_promotion_allowed": False,
        },
        "reproduce": (
            "py scripts/check_logos_studio_design_gate_v1.py --run-playwright-smoke "
            "--smoke-base https://logos.jema-ai.com"
        ),
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "out": str(args.output_json)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
