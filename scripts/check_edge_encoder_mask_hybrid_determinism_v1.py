#!/usr/bin/env python3
"""MASK hybrid router determinism: edge cache vs server replay [HYPO] B-track."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/edge_encoder_mask_hybrid_determinism_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--max-cases", type=int, default=5)
    ap.add_argument(
        "--corpus",
        type=Path,
        default=ROOT / "data/compression/stateless_poc_prospect_public-open-web-v1_v1.jsonl",
    )
    args = ap.parse_args()

    sys.path.insert(0, str(ROOT))
    from scripts.edge_encoder_spec_v1_lib import check_mask_hybrid_determinism

    errors, summary = check_mask_hybrid_determinism(
        workspace_root=ROOT,
        corpus_path=args.corpus,
        max_cases=args.max_cases,
    )

    doc = {
        "schema": "edge_encoder_mask_hybrid_determinism_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "track": "B",
        "hypothesis_tier": "B",
        "fail_comp_004": "MASK bench only — not COORD wire savings or Track A headline.",
        "ok": len(errors) == 0,
        "errors": errors,
        **summary,
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["ok"], "case_count": doc["case_count"], "errors": errors}, ensure_ascii=False))
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
