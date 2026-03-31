#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Emit rag_canary_rollback_flag_latest.json from vLLM canary repeat report."
    )
    ap.add_argument(
        "--input-report",
        default="reports/constitution/btrack_pilot/vllm_ab_canary_repeat_latest.json",
        help="Path to vLLM canary repeat JSON report",
    )
    ap.add_argument(
        "--out-flag",
        default="reports/constitution/btrack_pilot/rag_canary_rollback_flag_latest.json",
        help="Path to rollback flag JSON",
    )
    args = ap.parse_args()

    src = Path(args.input_report).resolve()
    out = Path(args.out_flag).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    if not src.exists():
        flag = {
            "schema": "rag_turboquant_canary_rollback_flag_v1",
            "should_rollback": True,
            "reason": "vllm_canary_report_missing",
            "source_report": str(src),
        }
        out.write_text(json.dumps(flag, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"WROTE: {out}")
        print("[vllm-canary-flag] BLOCK: source report missing -> rollback=true")
        return 1

    data = json.loads(src.read_text(encoding="utf-8"))
    if bool(data.get("skipped", False)):
        print("[vllm-canary-flag] SKIP: canary report marked skipped; keeping existing rollback flag")
        return 0

    stable = bool(data.get("stable", False))
    summary = data.get("summary") or {}
    go_rate = summary.get("go_rate")

    flag = {
        "schema": "rag_turboquant_canary_rollback_flag_v1",
        "should_rollback": (not stable),
        "reason": "vllm_canary_unstable" if not stable else "vllm_canary_stable",
        "source_report": str(src),
        "meta": {
            "stable": stable,
            "go_rate": go_rate,
            "candidate_model": data.get("candidate_model"),
            "baseline_model": data.get("baseline_model"),
        },
    }
    out.write_text(json.dumps(flag, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"WROTE: {out}")
    return 0 if stable else 1


if __name__ == "__main__":
    raise SystemExit(main())
