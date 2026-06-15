"""Reconcile tri-vertical commander signoff onto child promotion envelopes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
TRI_HUMAN_SIGNOFF = ROOT / "reports/compression_deep_pack_tri_vertical_human_signoff_latest.json"
CHILD_ENVELOPES = [
    ROOT / "docs/final/artifacts/compression_coding_deep_pack_promotion_signoff_envelope_v1_latest.json",
    ROOT / "docs/final/artifacts/compression_en_business_deep_pack_promotion_signoff_envelope_v1_latest.json",
    ROOT / "docs/final/artifacts/compression_ko_premium_cs_deep_pack_promotion_signoff_envelope_v1_latest.json",
]


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def patch_child_envelopes(*, reviewer: str, note: str | None, approved_at: str) -> list[str]:
    patched: list[str] = []
    for path in CHILD_ENVELOPES:
        if not path.is_file():
            continue
        doc = _load(path)
        hs = dict(doc.get("human_signoff") or {})
        hs["reviewer"] = reviewer
        hs["approved_at_utc"] = approved_at
        if note:
            hs["note"] = note
        doc["human_signoff"] = hs
        doc["envelope_status"] = "commander_signed_research_envelope"
        path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        patched.append(path.as_posix())
    return patched


def reconcile_from_tri_signoff_record(*, tri_signoff_path: Path = TRI_HUMAN_SIGNOFF) -> list[str]:
    tri = _load(tri_signoff_path)
    if not tri.get("approved"):
        return []
    reviewer = str(tri.get("reviewer") or "").strip()
    if not reviewer:
        return []
    approved_at = str(tri.get("approved_at_utc") or tri.get("recorded_at_utc") or "")
    note = str(tri.get("note") or "") or None
    return patch_child_envelopes(reviewer=reviewer, note=note, approved_at=approved_at)
