#!/usr/bin/env python3
"""Aggregate per-domain track_b_semantic_eval outputs into by_domain_latest."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description="Build trackb_semantic_eval_by_domain_latest.json")
    ap.add_argument(
        "--domains",
        default="medical,finance,policy",
        help="Comma-separated domain keys matching trackb_semantic_eval_{domain}_latest.json",
    )
    ap.add_argument("--semantic-min", type=float, default=0.8)
    ap.add_argument("--collision-max", type=float, default=0.01)
    ap.add_argument("--oov-max", type=float, default=0.15)
    ap.add_argument("--out", default=str(ART / "trackb_semantic_eval_by_domain_latest.json"))
    args = ap.parse_args()

    gates = {
        "semantic_score_min": args.semantic_min,
        "collision_rate_max": args.collision_max,
        "oov_rate_max": args.oov_max,
    }
    domains_out: dict[str, Any] = {}
    for d in [x.strip() for x in args.domains.split(",") if x.strip()]:
        p = ART / f"trackb_semantic_eval_{d}_latest.json"
        doc = json.loads(p.read_text(encoding="utf-8"))
        m = doc["metrics"]
        checks = {
            "semantic_ok": m["average_semantic_score"] >= gates["semantic_score_min"],
            "collision_ok": m["collision_rate_proxy"] <= gates["collision_rate_max"],
            "oov_ok": m["oov_rate_avg"] <= gates["oov_rate_max"],
        }
        domains_out[d] = {
            "artifact": str(p.resolve()).replace("\\", "/"),
            "metrics": m,
            "checks": checks,
        }

    all_ok = all(all(domains_out[d]["checks"].values()) for d in domains_out)
    out = {
        "schema": "trackb_semantic_eval_by_domain_v1",
        "generated_at_utc": _utc_now(),
        "domains": domains_out,
        "gates": gates,
        "decision": "GO_RESEARCH" if all_ok else "HOLD_RESEARCH",
        "out_of_scope": "No production promotion, no trading trigger.",
    }
    out_path = Path(args.out) if Path(args.out).is_absolute() else (ROOT / args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
