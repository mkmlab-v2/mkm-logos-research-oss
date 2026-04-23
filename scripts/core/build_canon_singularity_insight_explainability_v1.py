#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Build explainability sidecar for canon insight minimum.")
    ap.add_argument(
        "--insight-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_insight_minimum_v1.json",
    )
    ap.add_argument(
        "--output-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_insight_explainability_v1.json",
    )
    args = ap.parse_args()

    data = _read_json(Path(args.insight_json))
    rows = list(data.get("insights") or [])
    explain_rows: list[dict[str, Any]] = []
    for row in rows:
        score = float(row.get("score", 0.0))
        margin = float(row.get("margin_vs_second", 0.0))
        token_div = float(row.get("token_diversity", 0.0))
        comp = {
            "score_component": round(score, 6),
            "margin_component": round(margin, 6),
            "token_diversity_component": round(token_div, 6),
        }
        top_driver = max(comp.items(), key=lambda x: x[1])[0]
        explain_rows.append(
            {
                "row_id": row.get("row_id"),
                "best_regime": row.get("best_regime"),
                "components": comp,
                "top_driver": top_driver,
                "explanation_text": (
                    f"{row.get('row_id')}는 {row.get('best_regime')} 정렬에서 "
                    f"{top_driver} 기여가 상대적으로 큽니다."
                ),
            }
        )

    out = {
        "schema": "original_corpus_regime_singularity_canon_insight_explainability_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inputs": {"insight_json": str(args.insight_json)},
        "counts": {"rows": len(explain_rows)},
        "rows": explain_rows,
    }
    out_path = Path(args.output_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

