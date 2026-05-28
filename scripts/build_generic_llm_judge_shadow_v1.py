#!/usr/bin/env python3
"""B-track shadow LLM judge proxy from hybrid eval bridge (not a real LLM judge)."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from scripts.build_generic_llm_gate_inputs_v1 import _load_json, _quality_from_eval  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Build shadow judge_score from hybrid eval JSON")
    ap.add_argument(
        "--eval-json",
        default="reports/myeongri_hybrid_eval_bridge_latest.json",
    )
    ap.add_argument(
        "--out",
        default="reports/generic_llm_judge_latest.json",
    )
    args = ap.parse_args()

    root = Path(__file__).resolve().parents[1]
    eval_path = Path(args.eval_json)
    if not eval_path.is_absolute():
        eval_path = root / eval_path
    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = root / out_path

    if not eval_path.is_file():
        raise SystemExit(f"missing eval json: {eval_path}")

    eval_doc = _load_json(eval_path)
    score = _quality_from_eval(eval_doc)
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    payload: dict[str, Any] = {
        "schema": "generic_llm_judge_shadow_v1",
        "generated_at_utc": now,
        "judge_score": round(score, 4),
        "source_eval_json": str(eval_path).replace("\\", "/"),
        "method": "quality_proxy_from_hybrid_eval_bridge",
        "track_wall": {
            "hypothesis_tier": "B",
            "research_only": True,
            "note": "Not an LLM-as-judge run; proxy for gate wiring only",
        },
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "judge_score": payload["judge_score"], "out": str(out_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
