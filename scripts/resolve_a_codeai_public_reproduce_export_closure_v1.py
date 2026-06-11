#!/usr/bin/env python3
"""Resolve scripts import closure for a-codeai public reproduce export."""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_ENTRIES = (
    "scripts/run_compression_evidence_lv1_chain_v1.py",
    "scripts/run_customer_compression_stateless_poc_v1.py",
    "scripts/build_compression_public_reproduce_pack_v1.py",
    "scripts/build_compression_public_evidence_pack_v0_index_v1.py",
    "scripts/build_compression_media_fact_sheets_sync_v1.py",
    "scripts/build_compression_proof_project_closure_v1.py",
)


def _module_to_path(module: str) -> Path | None:
    if not module.startswith("scripts."):
        return None
    parts = module.split(".")
    py_file = ROOT / Path(*parts).with_suffix(".py")
    if py_file.is_file():
        return py_file
    init_file = ROOT / Path(*parts) / "__init__.py"
    if init_file.is_file():
        return init_file
    return None


def _imports_in_file(path: Path) -> set[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError):
        return set()
    mods: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("scripts"):
                    mods.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.startswith("scripts"):
                mods.add(node.module)
    return mods


def resolve_closure(entry_scripts: Iterable[str]) -> list[str]:
    queue: list[Path] = []
    seen: set[str] = set()
    for rel in entry_scripts:
        p = ROOT / rel.replace("\\", "/")
        if p.is_file():
            queue.append(p)

    while queue:
        path = queue.pop()
        rel = path.relative_to(ROOT).as_posix()
        if rel in seen:
            continue
        seen.add(rel)
        for mod in _imports_in_file(path):
            target = _module_to_path(mod)
            if target is None:
                continue
            trel = target.relative_to(ROOT).as_posix()
            if trel not in seen:
                queue.append(target)

    return sorted(seen)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--entry", action="append", dest="entries", default=[])
    ap.add_argument("--out-json", type=Path, default=None)
    args = ap.parse_args()
    entries = args.entries or list(DEFAULT_ENTRIES)
    paths = resolve_closure(entries)
    if args.out_json:
        out = args.out_json if args.out_json.is_absolute() else ROOT / args.out_json
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps({"schema": "a_codeai_export_closure_v1", "paths": paths}, indent=2) + "\n",
            encoding="utf-8",
        )
    print(json.dumps({"ok": True, "path_count": len(paths)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
