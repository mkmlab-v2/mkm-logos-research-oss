#!/usr/bin/env python3
"""Offline gate: mkm_ui_shell_contract_v1.json vs mkmlife shell components.

Validates consumer_portal_v1 (top nav + card deck) and operator_console_v1 (left sidebar)
stay separated. B-track / design surface only — not Track A or live trading GO.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs/final/artifacts/mkm_ui_shell_contract_v1.json"
DEFAULT_OUT = ROOT / "reports/mkm_ui_shell_contract_gate_v1_latest.json"


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path.resolve()).replace("\\", "/")


def _load_contract(contract_path: Path | None = None) -> dict[str, Any]:
    path = contract_path or CONTRACT
    if not path.is_file():
        raise FileNotFoundError(f"MISSING: {path}")
    doc = json.loads(path.read_text(encoding="utf-8"))
    if doc.get("schema") != "mkm_ui_shell_contract_v1":
        raise ValueError(f"bad schema: {doc.get('schema')!r}")
    return doc


def _find_hits(text: str, needles: list[str]) -> list[str]:
    hits: set[str] = set()
    for needle in needles:
        start = 0
        while True:
            idx = text.find(needle, start)
            if idx < 0:
                break
            window = text[max(0, idx - 24) : idx + len(needle) + 24]
            negated = any(
                token in window
                for token in (
                    "아닌",
                    "아닙니다",
                    "금지",
                    "forbidden",
                    "not a",
                    "not ",
                    "NO ",
                )
            )
            if not negated:
                hits.add(needle)
            start = idx + len(needle)
    return sorted(hits)


def _validate_consumer(shell: dict[str, Any], contract_doc: dict[str, Any], issues: list[str]) -> dict[str, Any]:
    layout = shell.get("layout") or {}
    if layout.get("sidebar") != "none":
        issues.append("consumer_portal_v1: sidebar must be none")
    if layout.get("nav") != "top":
        issues.append("consumer_portal_v1: nav must be top")

    primary = shell.get("primary_nav") or []
    max_nav = int(layout.get("max_primary_nav") or 5)
    if len(primary) > max_nav:
        issues.append(f"consumer_portal_v1: primary_nav count {len(primary)} > {max_nav}")
    if len(primary) != max_nav:
        issues.append(f"consumer_portal_v1: expected {max_nav} primary nav items, got {len(primary)}")

    components = shell.get("component_ssot") or {}
    header_rel = components.get("header")
    if not header_rel:
        issues.append("consumer_portal_v1: missing header component_ssot")
        return {"ok": False}

    header_path = ROOT / header_rel
    if not header_path.is_file():
        issues.append(f"consumer_portal_v1: missing header file {header_rel}")
        return {"ok": False}

    header_text = header_path.read_text(encoding="utf-8")
    nav_href_issues: list[str] = []
    for item in primary:
        href = item.get("href")
        if href and href not in header_text:
            nav_href_issues.append(f"missing href {href!r} in SiteHeader")

    copy_keys = shell.get("copy_keys") or {}
    copy_issues: list[str] = []
    for key, expected in copy_keys.items():
        if expected not in header_text and key.startswith("nav."):
            copy_issues.append(f"copy_keys[{key}]={expected!r} not in SiteHeader")

    scan_paths = shell.get("lint_scan_paths") or []
    forbidden: list[str] = []
    forbidden.extend(contract_doc.get("global_forbidden_surface_phrases") or [])
    forbidden.extend(contract_doc.get("global_forbidden_lens_terms") or [])
    scan_hits: list[dict[str, Any]] = []
    for rel in scan_paths:
        p = ROOT / rel
        if not p.is_file():
            issues.append(f"consumer lint_scan_paths missing: {rel}")
            continue
        text = p.read_text(encoding="utf-8")
        hits = _find_hits(text, forbidden)
        if hits:
            scan_hits.append({"path": rel, "hits": hits})

    shell_rel = components.get("shell")
    shell_path = ROOT / shell_rel if shell_rel else None
    if not shell_path or not shell_path.is_file():
        issues.append(f"consumer_portal_v1: missing shell component {shell_rel}")

    disclaimer_ids = shell.get("disclaimer_ids") or []
    disclaimer_blob = ""
    for rel in scan_paths + [shell_rel, header_rel]:
        if not rel:
            continue
        p = ROOT / rel
        if p.is_file():
            disclaimer_blob += p.read_text(encoding="utf-8")
    for extra in (
        "projects/mkm/mkm-life/app/ask-one/page.tsx",
        "projects/mkm/mkm-life/components/magic-orb/DisclaimerPanel.tsx",
        "projects/mkm/mkm-life/lib/report-builder.ts",
    ):
        p = ROOT / extra
        if p.is_file():
            disclaimer_blob += p.read_text(encoding="utf-8")
    missing_disclaimers = [d for d in disclaimer_ids if d not in disclaimer_blob]

    cross_import_path = ROOT / "projects/mkm/mkm-life/components/shell/OperatorConsoleShellV1.tsx"
    consumer_tree = ROOT / "projects/mkm/mkm-life/app"
    cross_import_hits: list[str] = []
    if cross_import_path.is_file():
        op_name = "OperatorConsoleShellV1"
        for tsx in consumer_tree.rglob("*.tsx"):
            if "shell" in tsx.parts and "OperatorConsoleShellV1" in tsx.name:
                continue
            text = tsx.read_text(encoding="utf-8")
            if op_name in text:
                cross_import_hits.append(_rel(tsx))

    if nav_href_issues:
        issues.extend(nav_href_issues)
    if copy_issues:
        issues.extend(copy_issues)
    if scan_hits:
        issues.append(f"consumer forbidden surface hits: {scan_hits}")
    if missing_disclaimers:
        issues.append(f"consumer missing disclaimer ids in surface: {missing_disclaimers}")
    if cross_import_hits:
        issues.append(f"consumer routes import operator shell: {cross_import_hits}")

    ok = not (
        nav_href_issues or copy_issues or scan_hits or missing_disclaimers or cross_import_hits
    )
    return {
        "shell_id": "consumer_portal_v1",
        "header": header_rel,
        "primary_nav_count": len(primary),
        "nav_href_ok": not nav_href_issues,
        "copy_ok": not copy_issues,
        "scan_hits": scan_hits,
        "disclaimer_ids": disclaimer_ids,
        "disclaimer_ok": not missing_disclaimers,
        "cross_import_ok": not cross_import_hits,
        "ok": ok,
    }


def _validate_operator(shell: dict[str, Any], issues: list[str]) -> dict[str, Any]:
    layout = shell.get("layout") or {}
    if layout.get("sidebar") != "left":
        issues.append("operator_console_v1: sidebar must be left")
    if layout.get("nav") != "sidebar":
        issues.append("operator_console_v1: nav must be sidebar")

    primary = shell.get("primary_nav") or []
    max_nav = int(layout.get("max_primary_nav") or 6)
    if len(primary) > max_nav:
        issues.append(f"operator_console_v1: primary_nav count {len(primary)} > {max_nav}")

    components = shell.get("component_ssot") or {}
    shell_rel = components.get("shell")
    shell_path = ROOT / shell_rel if shell_rel else None
    if not shell_path or not shell_path.is_file():
        issues.append(f"operator_console_v1: missing shell component {shell_rel}")
        return {"ok": False}

    shell_text = shell_path.read_text(encoding="utf-8")
    if "sidebar" not in shell_text.lower() and "site-shell-sidebar" not in shell_text:
        issues.append("operator_console_v1: shell missing sidebar marker")

    data_ssot = shell.get("data_ssot") or {}
    data_issues: list[str] = []
    for key, rel in data_ssot.items():
        p = ROOT / rel
        if not p.is_file():
            data_issues.append(f"missing data_ssot {key}={rel}")

    copy_keys = shell.get("copy_keys") or {}
    copy_issues = [k for k, v in copy_keys.items() if v not in shell_text]

    if data_issues:
        issues.extend(data_issues)
    if copy_issues:
        issues.append(f"operator shell missing copy keys: {copy_issues}")

    return {
        "shell_id": "operator_console_v1",
        "shell": shell_rel,
        "primary_nav_count": len(primary),
        "data_ssot_ok": not data_issues,
        "copy_ok": not copy_issues,
        "tenant_id": shell.get("tenant_id"),
        "lane": shell.get("lane"),
        "ok": not (data_issues or copy_issues),
    }


def run_check(
    *,
    contract_path: Path | None = None,
    write_report: bool = True,
    out_path: Path | None = None,
) -> tuple[int, dict[str, Any]]:
    issues: list[str] = []
    resolved_contract = contract_path or CONTRACT
    try:
        doc = _load_contract(resolved_contract)
    except (FileNotFoundError, ValueError) as exc:
        report = {"overall_ok": False, "error": str(exc)}
        if write_report:
            _write_report(report, out_path)
        print(json.dumps(report, ensure_ascii=False), file=sys.stderr)
        return 1, report

    shells = doc.get("shells") or {}
    consumer = shells.get("consumer_portal_v1")
    operator = shells.get("operator_console_v1")
    if not consumer or not operator:
        issues.append("missing consumer_portal_v1 or operator_console_v1 shell block")

    consumer_result: dict[str, Any] = {}
    operator_result: dict[str, Any] = {}
    if consumer:
        consumer_result = _validate_consumer(consumer, doc, issues)
    if operator:
        operator_result = _validate_operator(operator, issues)

    overall_ok = not issues and consumer_result.get("ok") and operator_result.get("ok")
    report = {
        "schema": "mkm_ui_shell_contract_gate_v1",
        "contract_path": _rel(resolved_contract),
        "overall_ok": overall_ok,
        "consumer_portal_v1": consumer_result,
        "operator_console_v1": operator_result,
        "issues": issues,
        "track_wall": "design_surface_only_no_track_a_no_live_trading",
    }
    if write_report:
        _write_report(report, out_path)
    print(json.dumps({"overall_ok": overall_ok, "issues": issues}, ensure_ascii=False))
    return (0 if overall_ok else 1), report


def _write_report(report: dict[str, Any], out_path: Path | None) -> None:
    path = out_path or DEFAULT_OUT
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate mkm_ui_shell_contract_v1.json")
    parser.add_argument("--contract", type=Path, default=CONTRACT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()
    code, _ = run_check(
        contract_path=args.contract,
        write_report=not args.no_write,
        out_path=args.out,
    )
    return code


if __name__ == "__main__":
    raise SystemExit(main())
