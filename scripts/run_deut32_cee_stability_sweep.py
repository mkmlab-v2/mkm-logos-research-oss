#!/usr/bin/env python3
"""Run Deut 32:8 CEE stability sweep across textual variants."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.core.cee_logic_core_v1 import CEEInput, run_cee_logic_core_v1

OUT = ROOT / "reports" / "constitution" / "btrack_pilot" / "deut32_cee_stability_sweep_v1.json"


CASES = (
    {
        "case_id": "base",
        "sons_of_god": ("בני אלהים עליון עמים נחלה", "בני אלהים עמים", "בני אלהים עליון עמים נחלה"),
        "sons_of_israel": ("בני ישראל עליון עמים נחלה גבול", "בני ישראל עמים", "בני ישראל עליון עמים נחלה גבול"),
    },
    {
        "case_id": "with_heaven_token",
        "sons_of_god": ("בני אלהים עליון שמים עמים נחלה", "בני אלהים שמים", "בני אלהים עליון שמים עמים נחלה"),
        "sons_of_israel": ("בני ישראל עליון שמים עמים נחלה גבול", "בני ישראל שמים", "בני ישראל עליון שמים עמים נחלה גבול"),
    },
    {
        "case_id": "short_compressed",
        "sons_of_god": ("בני אלהים עליון עמים נחלה", "בני אלהים", "בני אלהים עליון עמים נחלה"),
        "sons_of_israel": ("בני ישראל עליון עמים נחלה גבול", "בני ישראל", "בני ישראל עליון עמים נחלה גבול"),
    },
)


def _run_one(reading_id: str, triad: tuple[str, str, str], case_id: str) -> dict[str, object]:
    raw_text, compressed_text, reconstructed_text = triad
    out = run_cee_logic_core_v1(
        CEEInput(
            case_id=f"deut32_8::{case_id}::{reading_id}",
            raw_text=raw_text,
            compressed_text=compressed_text,
            reconstructed_text=reconstructed_text,
            corpus_type="dss",
            metadata={"target_ref": "Deut.32:8", "sweep_case_id": case_id},
        )
    )
    return {
        "reading_id": reading_id,
        "lambda_deviation": float(out["lambda_deviation"]),
        "state_id": out["state_id"],
        "distance_to_state16": out["distance_to_state16"],
        "vector_4d": out["vector_4d"],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Run CEE stability sweep for Deut 32:8")
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()

    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = ROOT / out_path

    case_rows = []
    winner_counter: Counter[str] = Counter()
    margins = []
    for case in CASES:
        rid = str(case["case_id"])
        god = _run_one("sons_of_god", case["sons_of_god"], rid)  # type: ignore[index]
        israel = _run_one("sons_of_israel", case["sons_of_israel"], rid)  # type: ignore[index]
        ordered = sorted([god, israel], key=lambda r: float(r["lambda_deviation"]))
        winner = str(ordered[0]["reading_id"])
        margin = round(float(ordered[1]["lambda_deviation"]) - float(ordered[0]["lambda_deviation"]), 6)
        winner_counter[winner] += 1
        margins.append(margin)
        case_rows.append(
            {
                "case_id": rid,
                "rows": ordered,
                "winner_reading_id": winner,
                "lambda_margin": margin,
            }
        )

    consensus_winner = winner_counter.most_common(1)[0][0] if winner_counter else None
    consensus_rate = (
        round(max(winner_counter.values()) / len(case_rows), 6)
        if case_rows
        else 0.0
    )
    mean_margin = round(sum(margins) / len(margins), 6) if margins else 0.0

    report = {
        "schema": "deut32_cee_stability_sweep_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "target_ref": "Deut.32:8",
        "case_count": len(case_rows),
        "cases": case_rows,
        "summary": {
            "consensus_winner": consensus_winner,
            "consensus_rate": consensus_rate,
            "mean_lambda_margin": mean_margin,
            "winner_counts": dict(winner_counter),
        },
        "communication_guardrail": {
            "preferred_terms": ["우세 가설", "stability sweep", "추가 검증 필요"],
            "forbidden_terms": ["정답 확정", "final accept"],
        },
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("OK: Deut32 CEE stability sweep generated")
    print(f"out={out_path}")
    print(f"consensus_winner={consensus_winner} consensus_rate={consensus_rate} mean_margin={mean_margin}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
