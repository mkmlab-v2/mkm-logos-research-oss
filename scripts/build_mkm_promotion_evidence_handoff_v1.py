#!/usr/bin/env python3
"""One-page promotion evidence handoff from existing SSOT artifacts (audit/review)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/mkm_promotion_evidence_handoff_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build() -> dict[str, Any]:
    pointer = _read(ROOT / "docs/final/artifacts/mkm_ai_status_pointer_latest.json")
    weekly = _read(ROOT / "docs/final/artifacts/mkm_ai_v2_weekly_readiness_report_latest.json")
    stability = _read(ROOT / "reports/mkm_ai_promotion_stability_summary_latest.json")
    exclusions = _read(ROOT / "docs/final/artifacts/mkm_ai_v2_weekly_exclusions_audit_v1_latest.json")
    edge = _read(ROOT / "reports/edge_m1_relay_chain_status_latest.json")

    repro = [
        "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\Invoke-MkmAiV2DailyReadiness.ps1 -SkipIntegratedGovernanceBuild",
        "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\Invoke-MkmPromotionStabilityCheck_v1.ps1",
        "py scripts/probe_mkmlife_magic_orb_live_v1.py",
    ]

    return {
        "schema": "mkm_promotion_evidence_handoff_v1",
        "generated_at_utc": _utc(),
        "summary_ko": (
            "주간 pass_rate 집계는 audited exclusions 적용; raw readiness log는 미변경. "
            "pointer·stability·edge M1은 일일 체인 말미에 재동기화."
        ),
        "promotion_status": pointer.get("status") if pointer else None,
        "weekly_pass_rate_percent": weekly.get("pass_rate_percent") if weekly else None,
        "weekly_sample_count": weekly.get("sample_count") if weekly else None,
        "stability": stability.get("stable") if stability else None,
        "edge_combined_pass": edge.get("combined_pass") if edge else None,
        "exclusions_one_liner": exclusions.get("one_liner") if exclusions else None,
        "boundary": {
            "track_a_auto_promote": False,
            "research_only_b_track": True,
            "is_final_product_llm": False,
        },
        "reproduce_commands": repro,
        "artifact_paths": {
            "pointer": "docs/final/artifacts/mkm_ai_status_pointer_latest.json",
            "weekly": "docs/final/artifacts/mkm_ai_v2_weekly_readiness_report_latest.json",
            "stability": "reports/mkm_ai_promotion_stability_summary_latest.json",
            "exclusions_audit": "docs/final/artifacts/mkm_ai_v2_weekly_exclusions_audit_v1_latest.json",
            "edge": "reports/edge_m1_relay_chain_status_latest.json",
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    doc = build()
    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
