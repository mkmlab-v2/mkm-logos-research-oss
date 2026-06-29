#!/usr/bin/env python3
"""Render myeongni_full_report_v1 JSON (stdin) to markdown (stdout)."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts" / "build_myeongni_full_report_v1.py"


def _load_builder():
    spec = importlib.util.spec_from_file_location("build_myeongni_full_report_v1", BUILDER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot_load_builder:{BUILDER}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    raw = sys.stdin.read()
    if not raw.strip():
        print("empty_stdin", file=sys.stderr)
        return 2
    doc = json.loads(raw)
    if doc.get("schema") != "myeongni_full_report_v1":
        print("invalid_schema", file=sys.stderr)
        return 2
    mod = _load_builder()
    print(mod._markdown(doc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
