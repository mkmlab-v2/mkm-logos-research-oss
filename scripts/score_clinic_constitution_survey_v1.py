"""
Score MKM constitution survey pack → observation_proxies + ai_hypothesis (consumer lane).

B-track · [HYPO] · not clinical diagnosis. Calibrate offline against physician_gold lane only.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.import_clinic_mvp_from_patient_registry_v1 import (  # noqa: E402
    observation_proxies_from_intake,
)
from scripts.lookup_gtm_mai_archetype_v1 import build_mai_public_card  # noqa: E402

BANK_REL = Path("docs/final/artifacts/clinic_constitution_survey_item_bank_v1.json")
PROXY_KEYS = ("cold_heat_lean", "digestion_lean", "activity_lean", "moisture_lean")
FOUR = ("taeeum", "soyang", "taeyang", "soeum")

def _proxy_contrib(norm: float, direction: str) -> float:
    if direction in ("heat", "high", "moist"):
        return norm
    if direction in ("cold", "low", "dry"):
        return 1.0 - norm
    return norm


def _workspace_root() -> Path:
    return _ROOT


def load_survey_bank(root: Path | None = None) -> dict[str, Any]:
    path = (root or _workspace_root()) / BANK_REL
    return json.loads(path.read_text(encoding="utf-8"))


def _norm_response(value: int, scale_max: int = 4) -> float:
    if scale_max <= 0:
        return 0.5
    return max(0.0, min(1.0, float(value) / float(scale_max)))


def score_survey_responses(
    bank: dict[str, Any],
    responses: dict[str, int],
) -> dict[str, Any]:
    """responses: item_id -> 0..scale_max."""
    scale_max = int((bank.get("scale_default") or {}).get("max", 4))
    proxy_sum = {k: 0.0 for k in PROXY_KEYS}
    proxy_w = {k: 0.0 for k in PROXY_KEYS}
    hint_scores = {k: 0.0 for k in FOUR}

    answered = 0
    for item in bank.get("items") or []:
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("item_id") or "")
        if item_id not in responses:
            continue
        val = int(responses[item_id])
        norm = _norm_response(val, scale_max)
        answered += 1
        weight = float(item.get("weight") or 1.0)
        direction = str(item.get("direction") or "")
        axis = str(item.get("axis") or "")
        if axis in PROXY_KEYS:
            contrib = _proxy_contrib(norm, direction) * weight
            proxy_sum[axis] += contrib
            proxy_w[axis] += weight
        hints = item.get("constitution_hints") or {}
        if isinstance(hints, dict):
            for code, hint_w in hints.items():
                if code in hint_scores:
                    hint_scores[code] += norm * float(hint_w) * weight

    proxies: dict[str, float] = {}
    for k in PROXY_KEYS:
        if proxy_w[k] > 0:
            proxies[k] = round(proxy_sum[k] / proxy_w[k], 3)
        else:
            proxies[k] = 0.5

    if answered < 3:
        ai_constitution = "uncertain"
        confidence = 0.38
    else:
        best = max(hint_scores.items(), key=lambda x: x[1])
        second = sorted(hint_scores.values(), reverse=True)
        margin = (second[0] - second[1]) if len(second) > 1 else second[0]
        if best[1] < 0.35 or margin < 0.08:
            ai_constitution = "uncertain"
            confidence = round(0.4 + min(0.12, margin), 3)
        else:
            ai_constitution = best[0]
            confidence = round(min(0.72, 0.48 + margin * 0.8), 3)

    return {
        "observation_proxies": proxies,
        "ai_hypothesis": {
            "constitution": ai_constitution,
            "confidence": confidence,
            "model_id": str(bank.get("pack_id") or "mkm_constitution_survey"),
        },
        "survey_meta": {
            "n_items_answered": answered,
            "n_items_total": len(bank.get("items") or []),
            "hint_scores": {k: round(v, 4) for k, v in hint_scores.items()},
        },
    }


def infer_responses_from_intake(
    bank: dict[str, Any],
    intake: dict[str, Any],
) -> dict[str, int]:
    """Bootstrap: map intake text → pseudo 0..4 responses (registry backfill only)."""
    proxies = observation_proxies_from_intake(intake)
    scale_max = int((bank.get("scale_default") or {}).get("max", 4))

    def to_scale(lean: float) -> int:
        return int(round(max(0, min(scale_max, lean * scale_max))))

    axis_target = {
        "cold_heat_lean": proxies["cold_heat_lean"],
        "digestion_lean": proxies["digestion_lean"],
        "activity_lean": proxies["activity_lean"],
        "moisture_lean": proxies["moisture_lean"],
    }
    out: dict[str, int] = {}
    for item in bank.get("items") or []:
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("item_id") or "")
        axis = str(item.get("axis") or "")
        direction = str(item.get("direction") or "")
        lean = axis_target.get(axis, 0.5)
        if direction in ("cold", "low", "dry"):
            val = 1.0 - lean
        else:
            val = lean
        out[item_id] = to_scale(val)
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Score constitution survey pack v1")
    p.add_argument("--responses-json", type=str, default="", help="JSON object item_id->0..4")
    p.add_argument(
        "--intake-json",
        type=Path,
        default=None,
        help="Bootstrap pseudo-responses from patient intake (backfill only)",
    )
    p.add_argument("--out", type=Path, default=None)
    p.add_argument(
        "--stdin-json",
        action="store_true",
        help="Read JSON {responses:{item_id:int}} from stdin; print score JSON",
    )
    p.add_argument(
        "--with-mai",
        action="store_true",
        help="Append gtm_mai_public_card_v1 (consumer GTM wrapper; lookup only)",
    )
    p.add_argument(
        "--myeongri-bucket",
        type=str,
        default="E*",
        help="Optional myeongni day-element bucket for MAI lookup (default E*)",
    )
    args = p.parse_args(argv)
    root = _workspace_root()
    bank = load_survey_bank(root)

    if args.stdin_json:
        payload = json.loads(sys.stdin.read())
        if isinstance(payload.get("responses"), dict):
            responses = {str(k): int(v) for k, v in payload["responses"].items()}
        else:
            responses = {str(k): int(v) for k, v in payload.items()}
        result = score_survey_responses(bank, responses)
        result["responses"] = responses
        if args.with_mai:
            result["mai_public_card"] = build_mai_public_card(
                result["observation_proxies"],
                myeongri_bucket=args.myeongri_bucket,
                root=root,
            )
        print(json.dumps(result, ensure_ascii=False))
        return 0

    if args.responses_json.strip():
        payload = json.loads(args.responses_json)
        responses = {str(k): int(v) for k, v in payload.items()}
        result = score_survey_responses(bank, responses)
        if args.with_mai:
            result["mai_public_card"] = build_mai_public_card(
                result["observation_proxies"],
                myeongri_bucket=args.myeongri_bucket,
                root=root,
            )
        print(json.dumps(result, ensure_ascii=False))
        return 0

    if args.intake_json:
        intake_doc = json.loads(args.intake_json.read_text(encoding="utf-8"))
        intake = intake_doc.get("intake") or {}
        responses = infer_responses_from_intake(bank, intake)
    else:
        print("provide --responses-json or --intake-json", file=sys.stderr)
        return 1

    result = score_survey_responses(bank, responses)
    if args.with_mai:
        result["mai_public_card"] = build_mai_public_card(
            result["observation_proxies"],
            myeongri_bucket=args.myeongri_bucket,
            root=root,
        )
    result["responses"] = responses
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
