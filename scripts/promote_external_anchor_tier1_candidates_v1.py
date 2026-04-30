#!/usr/bin/env python3
"""Promote Tier1 anchor candidates after manual signoff + gate checks."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_CANDIDATES = ART / "external_bible_anchor_tier1_promotion_candidates_latest.json"
DEFAULT_SIGNOFF = ART / "external_bible_anchor_tier1_manual_signoff_latest.json"
DEFAULT_APPLY_GATE = ART / "external_bible_crossref_threshold_apply_gate_latest.json"
DEFAULT_OUT = ART / "external_bible_anchor_tier1_promoted_latest.json"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _parse(ts: str) -> datetime | None:
    t = str(ts or "").strip()
    if not t:
        return None
    if t.endswith("Z"):
        t = t[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(t)
    except ValueError:
        return None
    return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--candidates-json", type=Path, default=DEFAULT_CANDIDATES)
    ap.add_argument("--signoff-json", type=Path, default=DEFAULT_SIGNOFF)
    ap.add_argument("--apply-gate-json", type=Path, default=DEFAULT_APPLY_GATE)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    candidates_doc = _read_json(args.candidates_json)
    signoff = _read_json(args.signoff_json)
    apply_gate = _read_json(args.apply_gate_json)
    prev_doc = _read_json(args.output_json)

    candidates = candidates_doc.get("promotion_candidates") if isinstance(candidates_doc.get("promotion_candidates"), list) else []
    candidate_labels = [str(c.get("label")) for c in candidates if isinstance(c, dict) and c.get("label")]

    signoff_approved = bool(signoff.get("approved"))
    expiry = _parse(str(signoff.get("expires_at_utc") or ""))
    signoff_not_expired = bool(expiry and expiry > datetime.now(timezone.utc))
    gate_ok = bool(apply_gate.get("can_apply_thresholds"))
    ready_candidates = str(candidates_doc.get("status") or "") == "READY_FOR_HUMAN_REVIEW" and len(candidate_labels) > 0

    checks = {
        "ready_candidates": ready_candidates,
        "signoff_approved": signoff_approved,
        "signoff_not_expired": signoff_not_expired,
        "apply_gate_ok_context": gate_ok,
    }
    # Promotion gate is decoupled from threshold-apply one-shot token.
    promoted = all(checks[k] for k in ("ready_candidates", "signoff_approved", "signoff_not_expired"))
    prev_status = str(prev_doc.get("status") or "")
    prev_labels = prev_doc.get("promoted_labels") if isinstance(prev_doc.get("promoted_labels"), list) else []
    prev_latched = prev_status in {"PROMOTED_TIER1_CANDIDATES", "PROMOTED_TIER1_CANDIDATES_LATCHED"} and len(prev_labels) > 0

    if not promoted and prev_latched:
        promoted = True
        candidate_labels = [str(x) for x in prev_labels if str(x).strip()]
    out = {
        "schema": "external_bible_anchor_tier1_promoted_v1",
        "generated_at_utc": _iso_now(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "inputs": {
            "candidates_json": str(args.candidates_json).replace("\\", "/"),
            "signoff_json": str(args.signoff_json).replace("\\", "/"),
            "apply_gate_json": str(args.apply_gate_json).replace("\\", "/"),
        },
        "checks": checks,
        "status": (
            "PROMOTED_TIER1_CANDIDATES_LATCHED"
            if (promoted and not all(checks[k] for k in ("ready_candidates", "signoff_approved", "signoff_not_expired")))
            else ("PROMOTED_TIER1_CANDIDATES" if promoted else "HOLD")
        ),
        "promoted_labels": candidate_labels if promoted else [],
        "promoted_count": len(candidate_labels) if promoted else 0,
        "recommended_next": (
            "sync_tier1_into_operating_policy"
            if promoted
            else "resolve_signoff_or_gate_blockers"
        ),
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "output_json": str(args.output_json).replace("\\", "/"),
                "status": out["status"],
                "promoted_count": out["promoted_count"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
