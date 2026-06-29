#!/usr/bin/env python3
"""Gate: no1kmedi Universe Hub — token SSOT + shell gate + live smoke [HYPO].

Surface: app.jema-ai.com/hub (discover v3).
Writes reports/no1kmedi_hub_design_gate_v1_latest.json
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
INSPECTOR_TSX = ROOT / "projects/no1kmedi/src/components/shell/HubEvidenceInspectorV3.tsx"
FOOTER_TSX = ROOT / "projects/no1kmedi/src/components/shell/HubDiscoverGtmFooter.tsx"
CONTRACT = ROOT / "docs/final/artifacts/mkm_universe_hub_shell_contract_v2_draft.json"
SHELL_GATE_SCRIPT = ROOT / "scripts/check_mkm_universe_hub_shell_v2.py"
LIVE_SMOKE_SCRIPT = ROOT / "scripts/smoke_universe_hub_live_v1.py"
PLAYWRIGHT_SMOKE_SCRIPT = ROOT / "projects/no1kmedi/scripts/smoke-hub-discover-cream-playwright-v1.mjs"
LIVE_SMOKE_REPORT = ROOT / "reports/universe_hub_live_smoke_v1_latest.json"
PLAYWRIGHT_SMOKE_REPORT = ROOT / "reports/hub_discover_cream_playwright_smoke_v1_latest.json"
SHELL_GATE_REPORT = ROOT / "reports/mkm_universe_hub_shell_gate_v2_latest.json"
OUT = ROOT / "reports/no1kmedi_hub_design_gate_v1_latest.json"

REQUIRED_CSS_MARKERS = (
    ".universe-hub-page--discover-v3",
    ".universe-hub-page--light-chrome.universe-hub-page--discover-v3",
    "--hub-bg: #faf7f2",
    "--hub-discover-accent: #2d7a68",
    ".universe-hub-main--hub-spoke",
    "padding: var(--space-xl) var(--space-lg)",
)

REQUIRED_TS_MARKERS = (
    "data-hub-inspector-discover-summary",
    "hub-discover-gtm-links-folded",
)

FORBIDDEN_COPY = (
    "47.5%",
    "0.890",
    "56.5%",
    "실매매 ON",
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


def _run(cmd: list[str], *, cwd: Path | None = None, timeout: int = 120) -> int:
    use_shell = sys.platform == "win32" and cmd and cmd[0] in {"npm", "npx"}
    proc = subprocess.run(
        cmd,
        cwd=str(cwd or ROOT),
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
        shell=use_shell,
    )
    return proc.returncode


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-live-smoke", action="store_true")
    ap.add_argument("--run-design-tokens", action="store_true")
    ap.add_argument("--run-playwright-smoke", action="store_true")
    ap.add_argument("--smoke-base", default="https://app.jema-ai.com")
    ap.add_argument("--output-json", type=Path, default=OUT)
    args = ap.parse_args(argv)

    css_text = GLOBALS_CSS.read_text(encoding="utf-8") if GLOBALS_CSS.is_file() else ""
    ts_text = INSPECTOR_TSX.read_text(encoding="utf-8") if INSPECTOR_TSX.is_file() else ""
    footer_text = FOOTER_TSX.read_text(encoding="utf-8") if FOOTER_TSX.is_file() else ""
    css_ok, css_missing = (True, []) if all(m in css_text for m in REQUIRED_CSS_MARKERS) else (
        False,
        [m for m in REQUIRED_CSS_MARKERS if m not in css_text],
    )
    ts_ok, ts_missing = (
        (True, [])
        if all(m in ts_text or m in footer_text for m in REQUIRED_TS_MARKERS)
        else (
            False,
            [m for m in REQUIRED_TS_MARKERS if m not in ts_text and m not in footer_text],
        )
    )

    contract_doc = _read_json(CONTRACT)
    plugins = ((contract_doc.get("shells") or {}).get("universe_hub_v2") or {}).get("sidebar_plugins") or []
    max_plugins = int(
        (((contract_doc.get("shells") or {}).get("universe_hub_v2") or {}).get("layout") or {}).get(
            "max_sidebar_plugins"
        )
        or 0
    )
    contract_ok = (
        contract_doc.get("schema") == "mkm_universe_hub_shell_contract_v2_draft"
        and len(plugins) <= max_plugins
        and max_plugins >= 1
    )

    shell_exit = _run([sys.executable, str(SHELL_GATE_SCRIPT)])
    shell_doc = _read_json(SHELL_GATE_REPORT)
    shell_ok = shell_exit == 0 and shell_doc.get("overall_ok") is True

    tokens_exit = 0
    if args.run_design_tokens:
        tokens_exit = _run(["npm", "run", "check:design-tokens"], cwd=ROOT / "projects/no1kmedi")
    tokens_ok = tokens_exit == 0 if args.run_design_tokens else GLOBALS_CSS.is_file()

    live_exit = 0
    if args.run_live_smoke:
        live_exit = _run([sys.executable, str(LIVE_SMOKE_SCRIPT)], timeout=90)
    live_doc = _read_json(LIVE_SMOKE_REPORT)
    live_checks = live_doc.get("checks") or []
    live_ok = live_doc.get("overall_ok") is True or (
        live_doc.get("ok") is True and not live_checks
    )
    if live_checks and live_doc.get("overall_ok") is None:
        live_ok = all(c.get("ok") for c in live_checks)
    if args.run_live_smoke:
        live_ok = live_ok and live_exit == 0

    pw_exit = 0
    pw_doc: dict[str, Any] = _read_json(PLAYWRIGHT_SMOKE_REPORT)
    if args.run_playwright_smoke:
        env = {**dict(**__import__("os").environ), "HUB_DISCOVER_SMOKE_BASE": args.smoke_base.rstrip("/")}
        pw_proc = subprocess.run(
            ["node", str(PLAYWRIGHT_SMOKE_SCRIPT)],
            cwd=str(ROOT / "projects/no1kmedi"),
            capture_output=True,
            text=True,
            check=False,
            timeout=180,
            env=env,
        )
        pw_exit = pw_proc.returncode
        pw_doc = _read_json(PLAYWRIGHT_SMOKE_REPORT)
    pw_ok = pw_doc.get("ok") is True and pw_doc.get("schema") == "hub_discover_cream_playwright_smoke_v1"
    pw_checks = len(pw_doc.get("checks") or [])

    forbidden_hits = [frag for frag in FORBIDDEN_COPY if frag in css_text]

    ok = css_ok and ts_ok and contract_ok and shell_ok and not forbidden_hits
    if args.run_design_tokens:
        ok = ok and tokens_ok and tokens_exit == 0
    if args.run_live_smoke:
        ok = ok and live_ok and live_exit == 0
    if args.run_playwright_smoke:
        ok = ok and pw_ok and pw_exit == 0

    out = {
        "schema": "no1kmedi_hub_design_gate_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "surface": "app.jema-ai.com/hub",
        "ok": ok,
        "checks": {
            "css_discover_v3_tokens": css_ok,
            "hub_inspector_ssot": ts_ok,
            "shell_contract_plugin_budget": contract_ok,
            "shell_gate_v2": shell_ok,
            "design_tokens_smoke": tokens_ok,
            "live_hub_smoke": live_ok,
            "playwright_cream_smoke_ok": pw_ok if args.run_playwright_smoke else None,
            "playwright_checks_count": pw_checks if args.run_playwright_smoke else None,
        },
        "plugin_count": len(plugins),
        "max_sidebar_plugins": max_plugins,
        "css_missing_markers": css_missing,
        "layout_missing_markers": ts_missing,
        "css_forbidden_hits": forbidden_hits,
        "design_reference": {
            "token_block": "projects/no1kmedi/src/app/globals.css (.universe-hub-page--discover-v3)",
            "skill": ".cursor/skills/mkm-design-lane/SKILL.md",
            "contract": str(CONTRACT),
        },
        "artifacts": {
            "shell_gate": str(SHELL_GATE_REPORT),
            "live_smoke": str(LIVE_SMOKE_REPORT),
            "playwright_smoke": str(PLAYWRIGHT_SMOKE_REPORT),
        },
        "live_smoke_summary": {
            "overall_ok": live_doc.get("overall_ok"),
            "checks_passed": sum(1 for c in live_checks if c.get("ok")),
            "checks_total": len(live_checks),
        },
        "reproduce": (
            "py scripts/check_no1kmedi_hub_design_gate_v1.py "
            "--run-design-tokens --run-live-smoke --run-playwright-smoke "
            "--smoke-base https://app.jema-ai.com"
        ),
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "out": str(args.output_json)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
