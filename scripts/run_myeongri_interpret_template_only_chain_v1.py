#!/usr/bin/env python3
"""Operational Harness v2 path: engine pillars + template envelope only (no LLM).

Recommended when interpret LoRA fails envelope contract. B-track only.

Example::

  py scripts/run_myeongri_interpret_template_only_chain_v1.py --limit 25
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

from scripts.myeongri_deterministic_lora_golden_views_v1 import (  # noqa: E402
    compact_expected_result,
    pillars_view,
)
from scripts.myeongri_interpret_envelope_views_v1 import (  # noqa: E402
    canonical_json,
    sha256_canonical,
    template_envelope_from_compact,
)
from scripts.prep_myeongri_deterministic_lora_golden_v1 import build_golden_row_dict  # noqa: E402

DEFAULT_GOLDEN = ROOT / "data/training/myeongri_deterministic_lora_golden_bulk_v1/locked_eval.jsonl"
DEFAULT_OUT = ROOT / "reports/myeongri_interpret_template_only_chain_v1_latest.json"
SCHEMA_PATH = ROOT / "docs/final/schemas/myeongri_ai_interpretation_envelope_v1.schema.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _validate_envelope(obj: dict[str, Any]) -> None:
    jsonschema = __import__("jsonschema")
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema).validate(obj)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--golden-jsonl", type=Path, default=DEFAULT_GOLDEN)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--limit", type=int, default=25)
    ap.add_argument("--lang", default="ko", choices=("ko", "en"))
    args = ap.parse_args()

    if not args.golden_jsonl.is_file():
        print(f"missing golden: {args.golden_jsonl}", file=sys.stderr)
        return 2
    if not SCHEMA_PATH.is_file():
        print(f"missing schema: {SCHEMA_PATH}", file=sys.stderr)
        return 2

    rows: list[dict] = []
    for line in args.golden_jsonl.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    rows = rows[: max(1, int(args.limit))]

    engine_ok = 0
    envelope_ok = 0
    per_row: list[dict[str, Any]] = []

    for row in rows:
        sid = str(row["sample_id"])
        exp = row["expected_result"]
        recomputed = build_golden_row_dict(
            str(row["birth_instant_utc"]),
            str(row["iana_tz"]),
            bool(row.get("is_male", False)),
            sid,
            str(row.get("split", "locked_eval")),
        )["expected_result"]
        eng_match = canonical_json(pillars_view(recomputed)) == canonical_json(pillars_view(exp))
        if eng_match:
            engine_ok += 1
        compact = compact_expected_result(recomputed)
        sha = sha256_canonical(compact)
        envelope = template_envelope_from_compact(
            compact, lang=args.lang, deterministic_input_sha256=sha, method_id="template_v1_ops_no_llm"
        )
        schema_ok = False
        try:
            _validate_envelope(envelope)
            schema_ok = True
            envelope_ok += 1
        except Exception as exc:  # noqa: BLE001
            note = str(exc)[:200]
        else:
            note = None
        per_row.append(
            {
                "sample_id": sid,
                "engine_pillars_match_golden": eng_match,
                "envelope_schema_valid": schema_ok,
                "deterministic_input_sha256": sha,
                "envelope": envelope,
            }
        )

    n = len(rows)
    report = {
        "schema": "myeongri_interpret_template_only_chain_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "mode": "engine_plus_template_envelope_no_llm",
        "golden_jsonl": str(args.golden_jsonl.relative_to(ROOT)).replace("\\", "/"),
        "rows": n,
        "engine_pillars_pass_rate": round(engine_ok / n, 6) if n else 0.0,
        "envelope_schema_valid_rate": round(envelope_ok / n, 6) if n else 0.0,
        "per_row": per_row,
        "track_wall": {"a_track_auto_promotion": False, "ready_for_external_send": False},
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": engine_ok == n and envelope_ok == n,
                "engine_pillars_pass_rate": report["engine_pillars_pass_rate"],
                "envelope_schema_valid_rate": report["envelope_schema_valid_rate"],
                "out": str(args.out_json),
            },
            ensure_ascii=False,
        )
    )
    return 0 if (engine_ok == n and envelope_ok == n) else 1


if __name__ == "__main__":
    raise SystemExit(main())
