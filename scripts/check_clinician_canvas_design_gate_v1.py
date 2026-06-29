#!/usr/bin/env python3
"""Gate: Clinician Trust Canvas stub — CSS SSOT + Playwright smoke [HYPO].

Surface: app.jema-ai.com /clinician?panel=copilot&canvas=1
Writes reports/clinician_canvas_design_gate_v1_latest.json
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
EMPTY_LAYOUT = ROOT / "projects/no1kmedi/src/components/clinician/ClinicianCanvasEmptyLayout.tsx"
GRAPH_PANEL = ROOT / "projects/no1kmedi/src/components/ClinicianConsultGraphPanel.tsx"
CONFLICT_SHEET = ROOT / "projects/no1kmedi/src/components/ClinicianGraphConflictSheet.tsx"
SHELL = ROOT / "projects/no1kmedi/src/components/trust-canvas/MkmTrustCanvasShell.tsx"
SMOKE_SCRIPT = ROOT / "projects/no1kmedi/scripts/smoke-clinician-canvas-playwright-v1.mjs"
SMOKE_REPORT = ROOT / "reports/clinician_canvas_playwright_smoke_v1_latest.json"
OUT = ROOT / "reports/clinician_canvas_design_gate_v1_latest.json"

REQUIRED_CSS_MARKERS = (
    ".clinician-canvas-page",
    ".clinician-canvas-page.clinician-canvas-theme",
    "--cc-surface-raised",
    ".clinician-canvas-page.clinician-canvas-theme .mkm-trust-canvas-citation-dock",
    ".clinician-canvas-graph-panel",
    "max-height: 38vh",
    ".clinician-canvas-citation-lock",
    ".workspace-link-btn",
)

REQUIRED_TS_MARKERS = (
    "ClinicianCanvasEmptyLayout",
    "clinician-canvas-theme",
    "clinician-canvas-graph-panel",
    "clinician-canvas-conflict-sheet",
    "data-tag-hold",
    "data-clinician-canvas-placeholder",
    "MkmTrustCanvasShell",
    "domainId=\"clinician\"",
)

FORBIDDEN_COPY = (
    "47.5%",
    "환각 0%",
    "Track A",
    "실매매",
    "자동 확정",
    "자동 처방",
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


def _check_markers(text: str, markers: tuple[str, ...]) -> tuple[bool, list[str]]:
    missing = [m for m in markers if m not in text]
    return len(missing) == 0, missing


def _run_playwright_smoke(base: str) -> tuple[int, dict[str, Any]]:
    env = {**dict(**__import__("os").environ), "CLINICIAN_CANVAS_SMOKE_BASE": base}
    proc = subprocess.run(
        ["node", str(SMOKE_SCRIPT)],
        cwd=str(ROOT / "projects" / "no1kmedi"),
        capture_output=True,
        text=True,
        check=False,
        timeout=180,
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
    ap.add_argument("--run-playwright-smoke", action="store_true")
    ap.add_argument("--smoke-base", default="https://app.jema-ai.com")
    ap.add_argument("--output-json", type=Path, default=OUT)
    args = ap.parse_args(argv)

    smoke_exit = 0
    smoke_doc: dict[str, Any] = _read_json(SMOKE_REPORT)
    if args.run_playwright_smoke:
        smoke_exit, smoke_doc = _run_playwright_smoke(args.smoke_base.rstrip("/"))

    css_text = GLOBALS_CSS.read_text(encoding="utf-8") if GLOBALS_CSS.is_file() else ""
    ts_parts = [EMPTY_LAYOUT, GRAPH_PANEL, CONFLICT_SHEET, SHELL]
    layout_text = "\n".join(p.read_text(encoding="utf-8") for p in ts_parts if p.is_file())
    css_ok, css_missing = _check_markers(css_text, REQUIRED_CSS_MARKERS)
    layout_ok, layout_missing = _check_markers(layout_text, REQUIRED_TS_MARKERS)
    copy_hits = [frag for frag in FORBIDDEN_COPY if frag in layout_text]
    copy_ok = len(copy_hits) == 0

    smoke_ok = smoke_doc.get("ok") is True and smoke_doc.get("schema") == "clinician_canvas_playwright_smoke_v1"
    checks_count = len(smoke_doc.get("checks") or [])

    ok = css_ok and layout_ok and copy_ok and smoke_ok and (not args.run_playwright_smoke or smoke_exit == 0)

    out = {
        "schema": "clinician_canvas_design_gate_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "surface": "app.jema-ai.com/clinician?panel=copilot&canvas=1",
        "ok": ok,
        "checks": {
            "css_token_ssot": css_ok,
            "empty_layout_ssot": layout_ok,
            "public_copy_guard": copy_ok,
            "playwright_smoke_ok": smoke_ok,
            "playwright_checks_count": checks_count,
        },
        "css_missing_markers": css_missing,
        "layout_missing_markers": layout_missing,
        "copy_forbidden_hits": copy_hits,
        "design_reference": {
            "token_block": "projects/no1kmedi/src/app/globals.css (.clinician-canvas-page)",
            "shell": "projects/no1kmedi/src/components/trust-canvas/MkmTrustCanvasShell.tsx",
            "pipeline": "MKM_TRUST_COMPOSITION_DESIGN_PIPELINE_V1.md",
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
            "py scripts/check_clinician_canvas_design_gate_v1.py --run-playwright-smoke "
            "--smoke-base https://app.jema-ai.com"
        ),
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "out": str(args.output_json)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
