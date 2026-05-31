#!/usr/bin/env python3
"""Audit narrative diversity on interpret SFT gold labels (oracle / no GPU)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.audit_myeongri_interpret_narrative_diversity_v1 import (  # noqa: E402
    V3_PREFIX,
    insight_to_template_skeleton,
)

DEFAULT_OUT = ROOT / "reports/myeongri_interpret_sft_oracle_diversity_audit_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(p).replace("\\", "/")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sft-jsonl", type=Path, required=True)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--v3-template-prefix", default=V3_PREFIX)
    args = ap.parse_args()

    if not args.sft_jsonl.is_file():
        print(f"missing sft: {args.sft_jsonl}", file=sys.stderr)
        return 2

    insights: list[str] = []
    method_ids: set[str] = set()
    for line in args.sft_jsonl.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        env = json.loads(str(row.get("output", "{}")))
        ins = str(env.get("mkm_advanced_insight") or "").strip()
        if ins:
            insights.append(ins)
        mid = env.get("method_id")
        if isinstance(mid, str) and mid:
            method_ids.add(mid)

    n = len(insights)
    skeletons = [insight_to_template_skeleton(i) for i in insights]
    skeleton_unique = len(set(skeletons))
    v3_prefix_hits = sum(1 for i in insights if i.startswith(args.v3_template_prefix))
    narrative_gate_pass = skeleton_unique > 1 and (v3_prefix_hits / n if n else 0.0) < 0.5

    report = {
        "schema": "myeongri_interpret_sft_oracle_diversity_audit_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "sft_jsonl": _rel(args.sft_jsonl),
        "rows_with_insight": n,
        "unique_insight_count": len(set(insights)),
        "unique_insight_rate": round(len(set(insights)) / n, 6) if n else 0.0,
        "template_skeleton_unique_count": skeleton_unique,
        "template_skeleton_unique_rate": round(skeleton_unique / n, 6) if n else 0.0,
        "v3_fixed_prefix_rate": round(v3_prefix_hits / n, 6) if n else 0.0,
        "method_id_unique_count": len(method_ids),
        "narrative_diversity_gate_pass": narrative_gate_pass,
        "interpretation": (
            "Oracle SFT labels — use before GPU train to confirm curriculum diversity."
        ),
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "skeleton_unique": skeleton_unique,
                "narrative_gate_pass": narrative_gate_pass,
                "out": str(args.out_json),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
