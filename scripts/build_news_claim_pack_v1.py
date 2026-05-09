#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
OUT_JSON = ART / "news_claim_pack_latest.json"
OUT_MD = ART / "news_claim_pack_latest.md"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    for enc in ("utf-8", "utf-8-sig"):
        try:
            return json.loads(path.read_text(encoding=enc))
        except Exception:
            continue
    return {}


def main() -> int:
    lb = _read(ART / "btrack_compression_leaderboard_latest.json")
    gate = _read(ART / "btrack_gate_r2_phase_sweep_latest.json")
    stress = _read(ART / "trackb_stress_benchmark_summary_latest.json")

    best_lb = lb.get("best_overall") or {}
    best_gate = gate.get("best_row") or {}
    stress_rec = stress.get("recommendation")

    payload = {
        "schema": "news_claim_pack_v1",
        "generated_at_utc": _utc_now(),
        "classification": "external_draft_non_binding",
        "status": "APPROVED_FOR_EXTERNAL_DRAFT",
        "claims_allowed": [
            f"Internal research benchmarks observed up to {best_lb.get('saving')} token saving while maintaining integrity 1.0.",
            f"High-savings profile showed jaccard around {best_lb.get('jaccard')} (internal benchmark context).",
            f"R2 gate sweep best row measured saving {best_gate.get('saving')} with integrity {best_gate.get('integrity')}.",
            f"Stress summary recommendation currently reports {stress_rec}.",
        ],
        "claims_forbidden": [
            "Do not claim guaranteed 99% compression in production.",
            "Do not claim independent third-party validation is complete.",
            "Do not equate manual-editorial external baseline with algorithmic ground truth.",
            "Do not claim automatic Track B to Track A production promotion.",
        ],
        "required_disclaimer": [
            "Metrics are internal research-lane observations and may vary by workload.",
            "External/public commitments require explicit governance approval.",
            "No live-trading or production trigger is implied by this benchmark package.",
        ],
        "evidence_refs": {
            "compression_leaderboard": "docs/final/artifacts/btrack_compression_leaderboard_latest.json",
            "gate_r2_sweep": "docs/final/artifacts/btrack_gate_r2_phase_sweep_latest.json",
            "stress_summary": "docs/final/artifacts/trackb_stress_benchmark_summary_latest.json",
        },
    }

    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md = [
        "# News Claim Pack (Draft v1)",
        "",
        f"- generated_at_utc: `{payload['generated_at_utc']}`",
        f"- status: `{payload['status']}`",
        "",
        "## Allowed Claims",
        *[f"- {x}" for x in payload["claims_allowed"]],
        "",
        "## Forbidden Claims",
        *[f"- {x}" for x in payload["claims_forbidden"]],
        "",
        "## Required Disclaimer",
        *[f"- {x}" for x in payload["required_disclaimer"]],
        "",
    ]
    OUT_MD.write_text("\n".join(md), encoding="utf-8")
    print(str(OUT_JSON))
    print(str(OUT_MD))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

