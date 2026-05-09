#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
OUT = ART / "external_baseline_claim_separation_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    payload = {
        "schema": "external_baseline_claim_separation_v1",
        "generated_at_utc": _utc_now(),
        "status": "ENFORCED_FOR_PUBLIC_COPY",
        "baseline_classification": "manual_editorial_heuristic",
        "algorithmic_ground_truth": False,
        "allowed_narrative": [
            "Use as calibration-oriented external reference only.",
            "Report overlap and sensitivity as exploratory context.",
        ],
        "forbidden_narrative": [
            "Do not present this baseline as objective algorithmic ground truth.",
            "Do not use this baseline alone as production promotion evidence.",
        ],
        "source_refs": {
            "overlap_comparison": "docs/final/artifacts/external_bible_crossref_overlap_comparison_latest.json",
            "health_check": "docs/final/artifacts/external_bible_crossref_health_check_latest.json",
        },
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(OUT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

