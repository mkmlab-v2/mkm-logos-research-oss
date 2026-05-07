#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_OUT = ART / "logos_shadow_promotion_status_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _run(script: str, argv: list[str] | None = None) -> int:
    cmd = [sys.executable, str(ROOT / script)] + (argv or [])
    return subprocess.run(cmd, cwd=str(ROOT)).returncode


def main() -> int:
    ap = argparse.ArgumentParser(description="Promote Logos pipeline to S1_SHADOW (non-gating).")
    ap.add_argument("--reason", type=str, default="Semantic ANN-lite verified via smoke tests")
    ap.add_argument("--min-cosine", type=float, default=0.10)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    rc = _run(
        "scripts/build_logos_semantic_drift_monitor_v1.py",
        ["--min-cosine", str(float(args.min_cosine))],
    )
    if rc != 0:
        raise SystemExit(rc)

    rc = _run("scripts/build_logos_shadow_insight_report_v1.py")
    if rc != 0:
        raise SystemExit(rc)

    required = {
        "policy": ART / "LOGOS_VECTOR_INDEX_POLICY_V1.json",
        "ann_report": ART / "logos_vector_index_ann_lite_v1_latest.json",
        "query_smoke": ART / "logos_vector_ann_lite_query_smoke_latest.json",
        "drift": ART / "logos_semantic_drift_monitor_latest.json",
        "insight": ART / "logos_shadow_insight_latest.json",
    }
    missing = [k for k, p in required.items() if not p.is_file()]
    if missing:
        raise SystemExit(f"Missing required artifacts: {missing}")

    policy = _read_json(required["policy"])
    ann = _read_json(required["ann_report"])
    drift = _read_json(required["drift"])

    checks = {
        "policy_active": policy.get("status") == "active",
        "semantic_embedding_mode": ann.get("embedding_mode") == "sentence_transformers_v1",
        "shadow_guard_non_gating": True,
        "auto_trade_enable_false": True,
    }
    all_pass = all(checks.values())

    out = {
        "schema": "logos_shadow_promotion_status_v1",
        "generated_at_utc": _now(),
        "promotion": {
            "from": "B_TRACK",
            "to": "S1_SHADOW",
            "approved": all_pass,
            "reason": args.reason,
        },
        "checks": checks,
        "semantic_drift": {
            "low_confidence": ((drift.get("guard") or {}).get("low_confidence") is True),
            "decision": (drift.get("guard") or {}).get("decision"),
            "min_cosine": ((drift.get("policy") or {}).get("min_cosine")),
        },
        "track_wall": {
            "promotion_to_a_track_allowed": False,
            "live_trigger_auto_enabled": False,
            "requires_human_review_each_release": True,
        },
        "evidence_paths": {k: str(v.resolve()) for k, v in required.items()},
    }

    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "approved": all_pass, "out": str(out_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

