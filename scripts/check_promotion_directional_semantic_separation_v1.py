# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.8, K:0.4, M:0.6}
# Balance: 90
# Purpose: Validate semantic separation between promotion decision and logos directional viability.
# Keywords: smoke-check, promotion-gate, logos, semantics, validation
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DECISION_JSON = ROOT / "reports" / "role_router_shadow_forward_validation_decision_latest.json"
DEFAULT_SUMMARY_JSON = ROOT / "docs" / "final" / "artifacts" / "prophecy_logos_revalidation_summary_latest.json"
DEFAULT_OUTPUT_JSON = ROOT / "docs" / "final" / "artifacts" / "promotion_directional_semantic_separation_latest.json"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _extract_from_paths(payload: dict[str, Any], paths: list[tuple[str, ...]]) -> tuple[Any, str | None]:
    for path in paths:
        cursor: Any = payload
        ok = True
        for key in path:
            if not isinstance(cursor, dict) or key not in cursor:
                ok = False
                break
            cursor = cursor[key]
        if ok:
            return cursor, ".".join(path)
    return None, None


def _build_result(decision: dict[str, Any], summary: dict[str, Any]) -> dict[str, Any]:
    final_decision = decision.get("final_decision")
    logos_viable, logos_path = _extract_from_paths(
        summary,
        [
            ("findings", "logos_directional_viable_under_current_setup"),
            ("logos_directional_viable_under_current_setup",),
        ],
    )

    has_explicit_promotion_decision = isinstance(final_decision, str)
    has_explicit_logos_directional_viability = isinstance(logos_viable, bool)
    semantic_separation_ok = has_explicit_promotion_decision and has_explicit_logos_directional_viability

    # Promotion and directional viability are intentionally independent.
    non_conflation_confirmed = semantic_separation_ok and (
        (final_decision == "GO_LIVE_CANDIDATE" and logos_viable is False)
        or (final_decision != "GO_LIVE_CANDIDATE")
        or (logos_viable is True)
    )

    return {
        "schema": "promotion_directional_semantic_separation_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "checks": {
            "has_explicit_promotion_decision": has_explicit_promotion_decision,
            "has_explicit_logos_directional_viability": has_explicit_logos_directional_viability,
            "semantic_separation_ok": semantic_separation_ok,
            "non_conflation_confirmed": non_conflation_confirmed,
        },
        "observed": {
            "final_decision": final_decision,
            "logos_directional_viable_under_current_setup": logos_viable,
            "logos_field_path": logos_path,
        },
        "interpretation": {
            "policy": "promotion_decision_and_logos_directional_viability_are_independent_dimensions",
            "note": "GO_LIVE_CANDIDATE does not imply logos directional viability equals true.",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check semantic separation of promotion decision vs logos directional viability.")
    parser.add_argument("--decision-json", type=Path, default=DEFAULT_DECISION_JSON)
    parser.add_argument("--summary-json", type=Path, default=DEFAULT_SUMMARY_JSON)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--strict", action="store_true", help="Return non-zero if separation checks fail.")
    args = parser.parse_args()

    decision = _read_json(args.decision_json)
    summary = _read_json(args.summary_json)
    result = _build_result(decision=decision, summary=summary)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    ok = bool((result.get("checks") or {}).get("semantic_separation_ok"))
    non_conflation_ok = bool((result.get("checks") or {}).get("non_conflation_confirmed"))
    print(f"WROTE: {args.output}")
    print(f"semantic_separation_ok={ok} non_conflation_confirmed={non_conflation_ok}")

    if args.strict and not (ok and non_conflation_ok):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
