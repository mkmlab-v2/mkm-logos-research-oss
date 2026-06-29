#!/usr/bin/env python3
"""Build en_tech OOV must_keep patch from P2 coverage report (B-track, research_only)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OOV = ROOT / "reports/constitution/btrack_pilot/comp_en_tech_oov_coverage_from_cpu_freeze_v1.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/en_tech_oov_must_keep_patch_v1.json"
FORBIDDEN = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_patch(
    oov_doc: dict[str, Any],
    *,
    min_case_frequency: int,
    max_tokens: int,
) -> dict[str, Any]:
    rows = oov_doc.get("top_missing_tokens") or []
    tokens: list[str] = []
    for row in rows:
        tok = str(row.get("token") or "").strip().lower()
        freq = int(row.get("case_frequency") or 0)
        if not tok or freq < min_case_frequency:
            continue
        tokens.append(tok)
        if len(tokens) >= max_tokens:
            break
    return {
        "schema": "en_tech_oov_must_keep_patch_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "lane_id": oov_doc.get("lane_id", "en_tech_spec_stress_v1"),
        "source_oov_report": "reports/constitution/btrack_pilot/comp_en_tech_oov_coverage_from_cpu_freeze_v1.json",
        "min_case_frequency": min_case_frequency,
        "max_tokens": max_tokens,
        "must_keep_tokens": tokens,
        "token_count": len(tokens),
        "track_a_active_written": False,
        "forbidden_write_path": str(FORBIDDEN.relative_to(ROOT)).replace("\\", "/"),
        "note": "Merged with BASE_MUST_KEEP at eval time only; does not modify 41k lexicon SSOT.",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--oov-json", type=Path, default=DEFAULT_OOV)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--min-case-frequency", type=int, default=75)
    ap.add_argument("--max-tokens", type=int, default=32)
    args = ap.parse_args()

    oov_path = (ROOT / args.oov_json).resolve() if not args.oov_json.is_absolute() else args.oov_json
    if not oov_path.is_file():
        print(f"error: missing {oov_path}", file=sys.stderr)
        return 1

    oov_doc = json.loads(oov_path.read_text(encoding="utf-8-sig"))
    out_doc = build_patch(
        oov_doc,
        min_case_frequency=args.min_case_frequency,
        max_tokens=args.max_tokens,
    )
    out_path = (ROOT / args.out_json).resolve() if not args.out_json.is_absolute() else args.out_json
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "wrote": str(out_path.relative_to(ROOT)).replace("\\", "/"),
                "token_count": out_doc["token_count"],
                "sample": out_doc["must_keep_tokens"][:8],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
