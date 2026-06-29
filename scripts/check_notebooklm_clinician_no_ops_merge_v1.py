#!/usr/bin/env python3
"""A4: physician_gold NL pack must not auto-merge 00_OPS / ops command sources."""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = ROOT / "scripts/build_notebooklm_clinician_sync_pack_v1.py"
CLINICIAN_PACK = ROOT / "reports/notebooklm_clinician_sync_pack_v1"
PUSH_NLM = ROOT / "scripts/push_notebooklm_clinician_pack_nlm_v1.py"
PUSH_MCP = ROOT / "scripts/push_notebooklm_clinician_pack_mcp_v1.py"

FORBIDDEN_PATH_FRAGMENTS = (
    "00_OPS",
    "notebooklm_ops_command",
    "MISSION_LOG",
    "mkm_chat_resume_pack",
    "CENTRAL_AGENT_MEMORY",
    "notebooklm_ltm_graph_ops",
)

FORBIDDEN_PACK_FILENAME_RE = re.compile(
    r"(?:^00_ops|ops_command|mission_log|central_agent|resume_pack)",
    re.I,
)

FORBIDDEN_PACK_CONTENT_RE = re.compile(
    r"(?:00_OPS_지휘부|notebooklm_ops_command_sync_pack|auto-?merge\s+ops|ops\s+notes?\s+into\s+clinician)",
    re.I,
)


def _pack_sources_from_build_script() -> list[str]:
    tree = ast.parse(BUILD_SCRIPT.read_text(encoding="utf-8"))
    for node in tree.body:
        targets_value: tuple[ast.AST | None, ast.AST | None] = (None, None)
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "PACK_SOURCES":
                    targets_value = (target, node.value)
                    break
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == "PACK_SOURCES":
            targets_value = (node.target, node.value)
        if targets_value[1] is not None:
            value = ast.literal_eval(targets_value[1])
            if isinstance(value, list):
                return [str(x) for x in value]
    raise ValueError("PACK_SOURCES not found in build_notebooklm_clinician_sync_pack_v1.py")


def check_build_script_sources() -> list[str]:
    errors: list[str] = []
    try:
        sources = _pack_sources_from_build_script()
    except (OSError, ValueError, SyntaxError) as exc:
        return [f"build_script_parse: {exc}"]
    for rel in sources:
        low = rel.replace("\\", "/").lower()
        for frag in FORBIDDEN_PATH_FRAGMENTS:
            if frag.lower() in low:
                errors.append(f"forbidden PACK_SOURCES entry: {rel} (matches {frag})")
    return errors


def check_push_scripts_pack_only() -> list[str]:
    errors: list[str] = []
    for script in (PUSH_NLM, PUSH_MCP):
        if not script.is_file():
            continue
        text = script.read_text(encoding="utf-8")
        if "notebooklm_ops_command_sync_pack" in text:
            errors.append(f"ops pack reference in {script.name}")
        if "notebooklm_clinician_sync_pack_v1" not in text:
            errors.append(f"clinician pack SSOT missing in {script.name}")
    return errors


def check_built_pack_if_present() -> list[str]:
    errors: list[str] = []
    index_path = CLINICIAN_PACK / "index.json"
    if not index_path.is_file():
        return errors
    index = json.loads(index_path.read_text(encoding="utf-8-sig"))
    if index.get("data_lane") != "physician_gold":
        errors.append("clinician pack index data_lane is not physician_gold")
    if index.get("ops_auto_merge_forbidden") is not True:
        errors.append("clinician pack index missing ops_auto_merge_forbidden: true")
    for name in index.get("files") or []:
        if not isinstance(name, str):
            continue
        if FORBIDDEN_PACK_FILENAME_RE.search(name):
            errors.append(f"forbidden pack filename: {name}")
    for meta in index.get("files_meta") or []:
        repo_path = str((meta or {}).get("repo_path") or "")
        low = repo_path.lower()
        for frag in FORBIDDEN_PATH_FRAGMENTS:
            if frag.lower() in low:
                errors.append(f"forbidden repo_path in pack meta: {repo_path}")
    for path in CLINICIAN_PACK.iterdir():
        if not path.is_file() or path.name in ("index.json", "00_clinician_lane_boundary_snippet.md"):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in FORBIDDEN_PACK_CONTENT_RE.finditer(text):
            start = max(0, match.start() - 40)
            end = min(len(text), match.end() + 40)
            window = text[start:end]
            if "금지" in window or "forbidden" in window.lower() or "never" in window.lower():
                continue
            errors.append(f"forbidden ops-merge phrase in pack file: {path.name}")
            break
    return errors


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--require-built-pack", action="store_true")
    args = ap.parse_args()

    errors: list[str] = []
    errors.extend(check_build_script_sources())
    errors.extend(check_push_scripts_pack_only())
    if args.require_built_pack and not (CLINICIAN_PACK / "index.json").is_file():
        errors.append("missing built pack: reports/notebooklm_clinician_sync_pack_v1/index.json")
    errors.extend(check_built_pack_if_present())

    out = ROOT / "reports/notebooklm_clinician_no_ops_merge_v1_latest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps({"ok": not errors, "errors": errors}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if errors:
        for err in errors:
            print(f"FAIL: {err}", file=sys.stderr)
        return 1
    print("OK: clinician NL pack has no ops auto-merge paths")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
