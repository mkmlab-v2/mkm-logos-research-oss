#!/usr/bin/env python3
"""Boundary guard: block unsanctioned numeric dosage in herbs/formulas clinical extract (B-track)."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_OUT = ROOT / "docs/final/artifacts/herbs_formulas_dosage_validation_latest.json"

DOSAGE_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(g|克|mg|毫克|毫升|ml|两|钱|片|粒|丸)",
    re.IGNORECASE,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _posix_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def scan_clinical_dosage_hits(doc: dict[str, Any]) -> list[dict[str, str]]:
    clinical = (doc.get("payload") or {}).get("clinical")
    if not isinstance(clinical, dict):
        return []
    hits: list[dict[str, str]] = []
    for key, value in clinical.items():
        text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
        for match in DOSAGE_RE.finditer(text):
            hits.append(
                {
                    "field": str(key),
                    "match": match.group(0),
                    "snippet": text[max(0, match.start() - 20) : match.end() + 20],
                }
            )
    return hits


def run_validate_dosage(doc: dict[str, Any]) -> dict[str, Any]:
    hits = scan_clinical_dosage_hits(doc)
    expert_required = bool(doc.get("expert_review_required"))
    ok = not hits or expert_required
    return {
        "schema": "herbs_formulas_dosage_validation_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "ok": ok,
        "dosage_hit_count": len(hits),
        "hits": hits,
        "expert_review_required": expert_required,
        "boundary_ack": doc.get("boundary_ack"),
        "research_only": True,
        "track_b_only": True,
        "send_gate": "HOLD",
        "policy": "Numeric dosage in clinical payload requires expert_review_required=true",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate herbs/formulas extract dosage boundary")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    in_path = args.input.resolve()
    if not in_path.is_file():
        print(json.dumps({"ok": False, "error": f"missing input: {in_path}"}, ensure_ascii=False))
        return 2

    doc = json.loads(in_path.read_text(encoding="utf-8"))
    report = run_validate_dosage(doc)
    report["input_path"] = _posix_path(in_path)

    out_path = args.out.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"ok": report["ok"], "out_path": _posix_path(out_path)}, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
