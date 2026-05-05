#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def main() -> int:
    ap = argparse.ArgumentParser(description="Build HYPO->FACT promotion status artifact.")
    ap.add_argument(
        "--external-template",
        default="docs/final/artifacts/external_fact_lock_template_v1.md",
    )
    ap.add_argument(
        "--internal-template",
        default="docs/final/artifacts/internal_decision_template_v1.md",
    )
    ap.add_argument(
        "--output-json",
        default="docs/final/artifacts/mkm_hypo_fact_promotion_status_latest.json",
    )
    args = ap.parse_args()

    p_ext = resolve(args.external_template)
    p_int = resolve(args.internal_template)
    out_path = resolve(args.output_json)

    ext_exists = p_ext.is_file()
    int_exists = p_int.is_file()

    ext_text = p_ext.read_text(encoding="utf-8-sig") if ext_exists else ""
    int_text = p_int.read_text(encoding="utf-8-sig") if int_exists else ""
    has_hypo_clause = ("Hypothesis" in ext_text) or ("[HYPO]" in int_text)
    has_non_claim_clause = "Non-Claim" in ext_text

    ready = ext_exists and int_exists and has_hypo_clause and has_non_claim_clause
    payload = {
        "schema": "mkm_hypo_fact_promotion_status_v1",
        "generated_at_utc": utc_now(),
        "inputs": {
            "external_template": str(p_ext),
            "internal_template": str(p_int),
        },
        "checks": {
            "external_template_exists": ext_exists,
            "internal_template_exists": int_exists,
            "hypothesis_clause_present": has_hypo_clause,
            "non_claim_clause_present": has_non_claim_clause,
        },
        "status": "READY_FOR_QUEUE_IMPLEMENTATION" if ready else "NEEDS_FIX",
        "next_action": (
            "Implement claim inbox queue and promotion workflow script."
            if ready
            else "Fix missing template clauses before queue integration."
        ),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
