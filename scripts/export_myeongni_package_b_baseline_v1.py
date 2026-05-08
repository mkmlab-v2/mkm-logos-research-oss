#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
FIX = ROOT / "tests" / "fixtures"

DEFAULT_SUMMARY = ART / "mkm_myeongni_package_b_chain_summary_latest.json"
DEFAULT_RECOMMEND = ART / "mkm_myeongni_profile_switch_recommendation_latest.json"
DEFAULT_POLICY = ART / "mkm_myeongni_profile_switch_policy_v1.json"
DEFAULT_OUT = FIX / "mkm_myeongni_package_b_baseline_v1.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Export versioned baseline pack from latest package_b chain outputs.")
    ap.add_argument("--summary-json", type=Path, default=DEFAULT_SUMMARY)
    ap.add_argument("--recommendation-json", type=Path, default=DEFAULT_RECOMMEND)
    ap.add_argument("--policy-json", type=Path, default=DEFAULT_POLICY)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    summary_path = args.summary_json if args.summary_json.is_absolute() else ROOT / args.summary_json
    rec_path = (
        args.recommendation_json if args.recommendation_json.is_absolute() else ROOT / args.recommendation_json
    )
    policy_path = args.policy_json if args.policy_json.is_absolute() else ROOT / args.policy_json

    summary = _read_json(summary_path)
    rec = _read_json(rec_path)
    policy = _read_json(policy_path)

    out = {
        "schema": "mkm_myeongni_package_b_baseline_v1",
        "generated_at_utc": _now(),
        "source_paths": {
            "summary_json": str(summary_path),
            "recommendation_json": str(rec_path),
            "policy_json": str(policy_path),
        },
        "snapshot": {
            "mode": summary.get("mode"),
            "direction_core": ((summary.get("snapshot") or {}).get("direction_core")),
            "decision_balanced": ((summary.get("snapshot") or {}).get("decision_balanced")),
            "decision_attack": ((summary.get("snapshot") or {}).get("decision_attack")),
            "recommended_profile": ((rec.get("state") or {}).get("recommended_profile")),
            "action": ((rec.get("state") or {}).get("action")),
        },
        "margins": summary.get("margins"),
        "policy": policy,
        "governance": {
            "research_only": True,
            "human_signoff_required": True,
            "note": "Versioned baseline fixture for reproducibility regression; do not use as live trigger.",
        },
    }

    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "snapshot": out["snapshot"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
