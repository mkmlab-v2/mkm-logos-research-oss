# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.72, L:0.85, K:0.48, M:0.62}
# Balance: 84
# Purpose: Emit a disabled-by-default insight sidecar next to btrack_prophecy_score_v1 (no row mutation).
# Keywords: btrack, prophecy, sidecar, phase3, insight
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCORE = ROOT / "docs" / "final" / "artifacts" / "btrack_prophecy_score_latest.json"
DEFAULT_BRIDGE = ROOT / "docs" / "final" / "artifacts" / "btrack_insight_promotion_bridge_index_v1_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "btrack_prophecy_score_insight_sidecar_v1_latest.json"

SCHEMA = "btrack_prophecy_score_insight_sidecar_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    return str(p.relative_to(ROOT)).replace("\\", "/")


def _optional_ref(p: Path) -> dict[str, Any]:
    return {"path": _rel(p), "exists": p.is_file()}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--bridge-index", type=Path, default=DEFAULT_BRIDGE)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--enable-experimental-attribution",
        action="store_true",
        help="Reserved; default build keeps experimental_attribution_enabled=false.",
    )
    args = ap.parse_args()

    score_schema: str | None = None
    if args.score_json.is_file():
        try:
            raw = json.loads(args.score_json.read_text(encoding="utf-8-sig"))
            if isinstance(raw, dict):
                score_schema = str(raw.get("schema") or "")
        except json.JSONDecodeError:
            score_schema = None

    lens_refs = {
        "logos_independent_lens_latest": _optional_ref(ROOT / "docs/final/artifacts/logos_independent_lens_latest.json"),
        "myeongni_independent_lens_latest": _optional_ref(
            ROOT / "docs/final/artifacts/myeongni_independent_lens_latest.json"
        ),
        "sasang_independent_lens_latest": _optional_ref(ROOT / "docs/final/artifacts/sasang_independent_lens_latest.json"),
    }

    out: dict[str, Any] = {
        "schema": SCHEMA,
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "paired_score_ref": _rel(args.score_json),
        "paired_score_schema": score_schema,
        "bridge_index_ref": _rel(args.bridge_index) if args.bridge_index.is_file() else None,
        "experimental_attribution_enabled": bool(args.enable_experimental_attribution),
        "lens_snapshot_refs": lens_refs,
        "feature_contract_v1": [
            "lens_majority_agreement_score_global",
            "notebooklm_guardrail_token_rate_prior_window",
            "myeongni_insight_log_lines_prior_window",
        ],
        "per_date_features": None,
        "notes_ko": [
            "stub: score JSON의 rows·predicted_direction는 변경하지 않음.",
            "승격·walkforward 게이트는 기존 btrack_prophecy_score_v1 입력만 사용.",
            "실험 병합은 별 계약·플래그·회귀 후 experimental_attribution_enabled=true에서만 검토.",
        ],
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(args.out.resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
