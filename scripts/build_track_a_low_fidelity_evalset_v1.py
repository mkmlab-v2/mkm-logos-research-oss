# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.8, L:0.9, K:0.3, M:0.2}
# Balance: 91
# Purpose: Build Track A low-fidelity evalset enriched with raw_text.
# Keywords: track_a, evalset, raw_text, low_fidelity, ssot
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ACTIVE = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
DEFAULT_INPUT = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "track_a_low_fidelity_evalset_v1.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--active-report", type=Path, default=DEFAULT_ACTIVE)
    ap.add_argument("--input-json", type=Path, default=DEFAULT_INPUT)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--max-jaccard", type=float, default=0.6)
    ap.add_argument("--target-domains", type=str, default="ssot,timing")
    args = ap.parse_args()

    active_path = args.active_report if args.active_report.is_absolute() else ROOT / args.active_report
    input_path = args.input_json if args.input_json.is_absolute() else ROOT / args.input_json
    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)

    active = json.loads(active_path.read_text(encoding="utf-8"))
    source = json.loads(input_path.read_text(encoding="utf-8"))
    source_map = {row.get("id"): row for row in source.get("compression_cases", [])}
    target_domains = {d.strip() for d in args.target_domains.split(",") if d.strip()}

    selected: list[dict[str, Any]] = []
    for row in (active.get("compression_metrics", {}) or {}).get("cases", []):
        domain = str(((row.get("route") or {}).get("domain")) or "unknown")
        jaccard = _safe_float(row.get("reconstruction_fidelity_jaccard"))
        if domain not in target_domains or jaccard > args.max_jaccard:
            continue
        case_id = str(row.get("id") or "")
        src = source_map.get(case_id, {})
        selected.append(
            {
                "id": case_id,
                "domain": domain,
                "reconstruction_fidelity_jaccard": jaccard,
                "token_saving_rate": _safe_float(row.get("token_saving_rate")),
                "raw_text": str(src.get("raw_text") or ""),
                "reconstructed_text_effective": str(row.get("reconstructed_text_effective") or ""),
                "compressed_text_effective": str(row.get("compressed_text_effective") or ""),
            }
        )

    out_doc = {
        "schema": "track_a_low_fidelity_evalset_v1",
        "generated_at_utc": _utc_now(),
        "inputs": {
            "active_report": str(active_path),
            "source_input": str(input_path),
        },
        "selection": {
            "target_domains": sorted(target_domains),
            "max_jaccard": args.max_jaccard,
            "selected_case_count": len(selected),
        },
        "cases": selected,
    }
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "out": str(out_path),
                "selected_case_count": len(selected),
                "first_case": selected[0]["id"] if selected else None,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
