#!/usr/bin/env python3
"""Validate v2 post-it markers on core managed pipeline files."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

TARGETS = [
    ROOT / "scripts" / "train_mkm_prophecy_lora_windows_fallback_v1.py",
    ROOT / "scripts" / "run_myeongri_deterministic_lora_inference_eval_v1.py",
    ROOT / "scripts" / "Run-MyeongriQwenSafeManagedPipeline_v1.ps1",
    ROOT / "scripts" / "Register-MyeongriQwenSafeManagedTask_v1.ps1",
]

REQUIRED_TOP = {"owner", "lane", "status", "evidence_mode", "metric_scope", "lifecycle"}
REQUIRED_METRIC_SCOPE = {"raw_metric", "repair_metric", "delta"}
REQUIRED_LIFECYCLE = {"phase", "replacement"}


def _extract_marker(text: str) -> dict[str, Any] | None:
    m = re.search(r"postit_v2:\s*(\{.+\})", text)
    if not m:
        return None
    return json.loads(m.group(1))


def _validate_marker(marker: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    missing_top = sorted(REQUIRED_TOP - set(marker.keys()))
    if missing_top:
        errs.append(f"missing top keys: {missing_top}")

    ms = marker.get("metric_scope")
    if not isinstance(ms, dict):
        errs.append("metric_scope must be object")
    else:
        missing_ms = sorted(REQUIRED_METRIC_SCOPE - set(ms.keys()))
        if missing_ms:
            errs.append(f"missing metric_scope keys: {missing_ms}")

    lc = marker.get("lifecycle")
    if not isinstance(lc, dict):
        errs.append("lifecycle must be object")
    else:
        missing_lc = sorted(REQUIRED_LIFECYCLE - set(lc.keys()))
        if missing_lc:
            errs.append(f"missing lifecycle keys: {missing_lc}")
    return errs


def main() -> int:
    failures: list[dict[str, Any]] = []
    for path in TARGETS:
        if not path.is_file():
            failures.append({"file": str(path), "error": "missing file"})
            continue
        text = path.read_text(encoding="utf-8-sig")
        marker = _extract_marker(text)
        if marker is None:
            failures.append({"file": str(path), "error": "missing postit_v2 marker"})
            continue
        errs = _validate_marker(marker)
        if errs:
            failures.append({"file": str(path), "error": "; ".join(errs)})

    out = {
        "schema": "postit_v2_validator_v1",
        "checked_files": [str(p) for p in TARGETS],
        "ok": len(failures) == 0,
        "failures": failures,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

