#!/usr/bin/env python3
"""Run Deut 32:8 CEE pilot for competing variant readings."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.core.cee_logic_core_v1 import CEEInput, run_cee_logic_core_v1

OUT = ROOT / "reports" / "constitution" / "btrack_pilot" / "deut32_cee_pilot_v1.json"

READINGS = (
    {
        "reading_id": "sons_of_god",
        "label": "bene elohim / sons of God",
        "raw_text": "בני אלהים עליון עמים נחלה",
        "compressed_text": "בני אלהים עמים",
        "reconstructed_text": "בני אלהים עליון עמים נחלה",
    },
    {
        "reading_id": "sons_of_israel",
        "label": "bene yisrael / sons of Israel",
        "raw_text": "בני ישראל עליון עמים נחלה גבול",
        "compressed_text": "בני ישראל עמים",
        "reconstructed_text": "בני ישראל עליון עמים נחלה גבול",
    },
)


def main() -> int:
    ap = argparse.ArgumentParser(description="Run CEE pilot for Deut 32:8 variant readings")
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()

    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = ROOT / out_path

    rows = []
    for r in READINGS:
        result = run_cee_logic_core_v1(
            CEEInput(
                case_id=f"deut32_8::{r['reading_id']}",
                raw_text=r["raw_text"],
                compressed_text=r["compressed_text"],
                reconstructed_text=r["reconstructed_text"],
                corpus_type="dss",
                metadata={"target_ref": "Deut.32:8", "reading_label": r["label"]},
            )
        )
        rows.append(
            {
                "reading_id": r["reading_id"],
                "label": r["label"],
                "lambda_deviation": result["lambda_deviation"],
                "state_id": result["state_id"],
                "distance_to_state16": result["distance_to_state16"],
                "vector_4d": result["vector_4d"],
            }
        )

    rows.sort(key=lambda x: float(x["lambda_deviation"]))
    winner = rows[0]
    runner = rows[1] if len(rows) > 1 else None
    margin = (
        round(float(runner["lambda_deviation"]) - float(winner["lambda_deviation"]), 6)
        if runner is not None
        else 0.0
    )

    report = {
        "schema": "deut32_cee_pilot_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "target_ref": "Deut.32:8",
        "method": "lower_lambda_deviation_wins",
        "rows": rows,
        "decision": {
            "winner_reading_id": winner["reading_id"],
            "winner_label": winner["label"],
            "lambda_margin": margin,
            "status": "provisional_accept" if margin > 0 else "hold_for_review",
            "communication_guardrail": {
                "preferred_terms": ["우세 가설", "provisional", "추가 검증 필요"],
                "forbidden_terms": ["정답 확정", "final accept"],
            },
        },
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("OK: Deut32 CEE pilot generated")
    print(f"out={out_path}")
    print(f"winner={winner['reading_id']} lambda_margin={margin}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
