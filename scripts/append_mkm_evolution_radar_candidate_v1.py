#!/usr/bin/env python3
"""Append one pending candidate to mkm_evolution_radar_daily_v1 (human approval queue only).

Does not apply repo changes, Track A promotion, or live trading. Exa/chat findings
enter the radar as pending — commander must say ``승인: <id>`` in a separate turn.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RADAR = ROOT / "reports" / "mkm_evolution_radar_daily_v1_latest.json"

REQUIRED_CANDIDATE_KEYS = (
    "id",
    "title",
    "source",
    "kind",
    "approval_status",
    "suggested_action",
)
PRESERVE_KINDS = frozenset(
    {
        "exa_product_fact_review",
        "human_review_queue",
        "manual_followup",
    }
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def validate_candidate(candidate: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in REQUIRED_CANDIDATE_KEYS:
        if not str(candidate.get(key) or "").strip():
            errors.append(f"missing or empty field: {key}")
    status = str(candidate.get("approval_status") or "")
    if status != "pending":
        errors.append("approval_status must be 'pending' on append")
    if candidate.get("auto_apply"):
        errors.append("auto_apply must be omitted or 'none'")
    return errors


def load_radar(path: Path) -> dict[str, Any]:
    if path.is_file():
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
        if doc.get("schema") != "mkm_evolution_radar_daily_v1":
            raise ValueError(f"unexpected schema in {path}")
        return doc
    return {
        "schema": "mkm_evolution_radar_daily_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "human_approval_required": True,
        "auto_apply": "none",
        "allowlist_ssot": "docs/final/artifacts/evolution_auto_apply_allowlist_v1_latest.json",
        "candidates": [],
        "commander_approval_contract": {
            "approve_phrase_examples": [
                "승인: exa_mcp_permissions_review",
                "승인: myeongri_interpret_v4_calibration30_review",
            ],
            "reject_phrase": "거절: <id>",
            "note_ko": (
                "승인 전 레포 자동 변경·Track A 승격·실매매 합선 금지. "
                "Exa fetch는 live fact 수집 로그이며 구현·통과 증명 아님."
            ),
        },
    }


def append_candidate(
    radar: dict[str, Any],
    candidate: dict[str, Any],
    *,
    replace: bool = False,
) -> tuple[dict[str, Any], str]:
    errors = validate_candidate(candidate)
    if errors:
        raise ValueError("; ".join(errors))

    cid = str(candidate["id"])
    candidates: list[dict[str, Any]] = list(radar.get("candidates") or [])
    for i, existing in enumerate(candidates):
        if str(existing.get("id")) == cid:
            if not replace:
                return radar, "skipped_duplicate"
            candidates[i] = candidate
            radar["candidates"] = candidates
            radar["generated_at_utc"] = _utc_now()
            return radar, "replaced"

    candidate.setdefault("appended_at_utc", _utc_now())
    candidate.setdefault("preserve_on_daily_rebuild", candidate.get("kind") in PRESERVE_KINDS)
    candidates.append(candidate)
    radar["candidates"] = candidates
    radar["generated_at_utc"] = _utc_now()
    return radar, "appended"


def preserved_candidates_from_radar(doc: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for c in doc.get("candidates") or []:
        if not isinstance(c, dict):
            continue
        if c.get("preserve_on_daily_rebuild") is True or c.get("kind") in PRESERVE_KINDS:
            out.append(c)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--radar-json", type=Path, default=DEFAULT_RADAR)
    ap.add_argument(
        "--from-json",
        type=Path,
        required=True,
        help="Single candidate object JSON (see docs/final/artifacts/fixtures/mkm_evolution_radar_candidate_*.example.json)",
    )
    ap.add_argument(
        "--replace",
        action="store_true",
        help="Replace existing candidate with same id",
    )
    args = ap.parse_args()

    if not args.from_json.is_file():
        print(f"missing: {args.from_json}", file=sys.stderr)
        return 2

    candidate = json.loads(args.from_json.read_text(encoding="utf-8-sig"))
    if not isinstance(candidate, dict):
        print("candidate must be a JSON object", file=sys.stderr)
        return 2

    radar = load_radar(args.radar_json)
    try:
        radar, action = append_candidate(radar, candidate, replace=args.replace)
    except ValueError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1

    args.radar_json.parent.mkdir(parents=True, exist_ok=True)
    args.radar_json.write_text(
        json.dumps(radar, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    try:
        radar_rel = str(args.radar_json.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        radar_rel = str(args.radar_json)
    pending = sum(
        1
        for c in radar.get("candidates") or []
        if isinstance(c, dict) and c.get("approval_status") == "pending"
    )
    print(
        json.dumps(
            {
                "ok": True,
                "action": action,
                "id": candidate.get("id"),
                "pending_count": pending,
                "radar": radar_rel,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
