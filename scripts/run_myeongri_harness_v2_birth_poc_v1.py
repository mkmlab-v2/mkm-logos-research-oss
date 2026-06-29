#!/usr/bin/env python3
"""Single-birth Harness v2 PoC: deterministic engine + template envelope (no LLM).

For mkmlife/jema-ai subprocess wiring. B-track [HYPO] only — not Track A promotion.

Example::

  py scripts/run_myeongri_harness_v2_birth_poc_v1.py \\
    --utc-instant 1992-03-12T17:00:00Z --iana-tz Asia/Seoul --is-male
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.myeongri_deterministic_lora_golden_views_v1 import compact_expected_result  # noqa: E402
from scripts.myeongri_interpret_envelope_views_v1 import (  # noqa: E402
    sha256_canonical,
    template_envelope_from_compact,
    validate_envelope_required_fields,
)
from scripts.prep_myeongri_deterministic_lora_golden_v1 import build_golden_row_dict  # noqa: E402

SCHEMA_PATH = ROOT / "docs/final/schemas/myeongri_ai_interpretation_envelope_v1.schema.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_harness_v2_birth_poc_v1(
    *,
    utc_instant: str,
    iana_tz: str,
    is_male: bool,
    lang: str = "ko",
    sample_id: str = "ad_hoc_birth_v1",
) -> dict[str, Any]:
    row = build_golden_row_dict(utc_instant, iana_tz, is_male, sample_id, "poc_ad_hoc")
    expected = row["expected_result"]
    compact = compact_expected_result(expected)
    sha = sha256_canonical(compact)
    envelope = template_envelope_from_compact(
        compact,
        lang=lang,
        deterministic_input_sha256=sha,
        method_id="harness_v2_birth_poc_template_v1",
    )
    schema_note = validate_envelope_required_fields(envelope)
    return {
        "schema": "myeongri_harness_v2_birth_poc_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "research_only": True,
        "mode": "engine_plus_template_envelope_no_llm",
        "birth_instant_utc": utc_instant,
        "iana_tz": iana_tz,
        "is_male": bool(is_male),
        "deterministic_input_sha256": sha,
        "engine_result": expected,
        "compact": compact,
        "interpretation_envelope": envelope,
        "envelope_contract_ok": schema_note == "",
        "envelope_contract_note": schema_note or None,
        "harness_path": "scripts/run_myeongri_harness_v2_birth_poc_v1.py",
        "track_wall": {
            "a_track_auto_promotion": False,
            "ready_for_external_send": False,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--utc-instant", required=True, help="Birth instant UTC (ISO Z)")
    ap.add_argument("--iana-tz", required=True, help="IANA timezone e.g. Asia/Seoul")
    ap.add_argument("--is-male", action="store_true", default=False)
    ap.add_argument("--lang", default="ko", choices=("ko", "en"))
    ap.add_argument("--sample-id", default="ad_hoc_birth_v1")
    ap.add_argument("--compact", action="store_true", help="Single-line JSON stdout")
    ap.add_argument(
        "--out-json",
        type=Path,
        default=None,
        help="Optional report path (default: stdout only)",
    )
    args = ap.parse_args()

    if not SCHEMA_PATH.is_file():
        print(f"missing schema: {SCHEMA_PATH}", file=sys.stderr)
        return 2

    doc = build_harness_v2_birth_poc_v1(
        utc_instant=args.utc_instant.strip(),
        iana_tz=args.iana_tz.strip(),
        is_male=bool(args.is_male),
        lang=args.lang,
        sample_id=str(args.sample_id),
    )
    if args.out_json:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.compact:
        print(json.dumps(doc, ensure_ascii=False, separators=(",", ":")))
    else:
        print(json.dumps(doc, ensure_ascii=False, indent=2))
    return 0 if doc.get("envelope_contract_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
