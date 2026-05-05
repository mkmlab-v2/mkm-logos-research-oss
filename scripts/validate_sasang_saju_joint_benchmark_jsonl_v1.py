#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Structural validation for ``sasang_saju_joint_benchmark_row_v1`` JSONL rows."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PATH = ROOT / "data" / "myeongni" / "sasang_saju_joint_benchmark_v1.jsonl"

_SCHEMA = "sasang_saju_joint_benchmark_row_v1"
_REQUIRED_ROOT = ("schema", "person_id", "benchmark_tier", "privacy_tier", "provenance")
_ISO_Z = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$")


def _errs_for_row(row: dict[str, Any], *, line_no: int) -> list[str]:
    errs: list[str] = []
    if str(row.get("schema") or "") != _SCHEMA:
        errs.append(f"line {line_no}: schema must be {_SCHEMA!r}")
    for k in _REQUIRED_ROOT:
        if not str(row.get(k) or "").strip():
            errs.append(f"line {line_no}: missing or empty {k!r}")
    br = row.get("birth_resolution")
    if br is not None and not isinstance(br, dict):
        errs.append(f"line {line_no}: birth_resolution must be object or null")
    elif isinstance(br, dict) and br:
        bi = str(br.get("birth_instant_utc") or "").strip()
        tz = str(br.get("iana_tz") or "").strip()
        if not bi:
            errs.append(f"line {line_no}: birth_resolution.birth_instant_utc required when birth set")
        elif not _ISO_Z.match(bi):
            errs.append(f"line {line_no}: birth_instant_utc must be ISO8601 ending with Z")
        if not tz:
            errs.append(f"line {line_no}: birth_resolution.iana_tz required when birth set")
        if "is_male" not in br:
            errs.append(f"line {line_no}: birth_resolution.is_male required when birth set")
    seo = row.get("saju_engine_output_v1")
    if isinstance(seo, dict) and seo.get("pillars") is not None:
        pil = seo.get("pillars")
        if not isinstance(pil, dict):
            errs.append(f"line {line_no}: saju_engine_output_v1.pillars must be object")
        else:
            for k in ("year", "month", "day", "hour"):
                if not str(pil.get(k) or "").strip():
                    errs.append(f"line {line_no}: empty pillar {k!r}")
    return errs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--path", type=Path, default=DEFAULT_PATH)
    args = ap.parse_args()

    if not args.path.is_file():
        print(json.dumps({"ok": False, "error": f"missing {args.path}"}, ensure_ascii=False))
        return 2

    all_errs: list[str] = []
    n = 0
    for line_no, line in enumerate(args.path.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as e:
            all_errs.append(f"line {line_no}: json: {e}")
            continue
        if not isinstance(row, dict):
            all_errs.append(f"line {line_no}: row must be object")
            continue
        n += 1
        all_errs.extend(_errs_for_row(row, line_no=line_no))

    ok = not all_errs
    print(json.dumps({"ok": ok, "rows": n, "errors": all_errs}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
