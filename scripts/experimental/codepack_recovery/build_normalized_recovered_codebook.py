#!/usr/bin/env python3
"""Build a master_codebook_dual_track-compatible artifact from recovered archive assets."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "scripts" / "experimental" / "codepack_recovery"
OUT = ROOT / "docs" / "final" / "artifacts" / "normalized_recovered_codebook_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _mk_lookup_entry(
    *,
    lookup_id: str,
    domain: str,
    input_key: str,
    canonical_output: dict[str, Any],
    source_refs: list[str],
) -> dict[str, Any]:
    return {
        "lookup_id": lookup_id,
        "domain": domain,
        "input_key": input_key,
        "canonical_output": canonical_output,
        "source_refs": source_refs,
        "status": "active",
    }


def main() -> int:
    sovereign = _load_json(BASE / "data" / "sovereign_codebook.json")
    education = _load_json(BASE / "data" / "education_codebook.json")

    patterns = sovereign.get("patterns") if isinstance(sovereign, dict) else None
    if not isinstance(patterns, list):
        raise SystemExit("Invalid sovereign_codebook.json: patterns(list) required")

    edu_patterns = education.get("patterns") if isinstance(education, dict) else None
    if not isinstance(edu_patterns, list):
        raise SystemExit("Invalid education_codebook.json: patterns(list) required")

    lookup_entries: list[dict[str, Any]] = []
    for p in patterns:
        if not isinstance(p, dict):
            continue
        name = str(p.get("pattern_name", "")).strip()
        if not name:
            continue
        lookup_entries.append(
            _mk_lookup_entry(
                lookup_id=f"other.recovered.sovereign.{name.lower()}",
                domain="other",
                input_key=name,
                canonical_output={
                    "pattern_name": name,
                    "trading_signal": p.get("trading_signal"),
                    "confidence": p.get("confidence"),
                    "vector_4d": p.get("vector_4d"),
                    "prophecy": p.get("prophecy"),
                },
                source_refs=[
                    "scripts/experimental/codepack_recovery/data/sovereign_codebook.json",
                    "scripts/experimental/codepack_recovery/core/mkm_sovereign_codebook.py",
                ],
            )
        )

    for p in edu_patterns:
        if not isinstance(p, dict):
            continue
        pid = str(p.get("id", "")).strip()
        text = str(p.get("text", "")).strip()
        if not pid or not text:
            continue
        lookup_entries.append(
            _mk_lookup_entry(
                lookup_id=f"other.recovered.education.{pid.lower()}",
                domain="other",
                input_key=text,
                canonical_output={"marker_id": pid, "text": text, "domain": "education"},
                source_refs=[
                    "scripts/experimental/codepack_recovery/data/education_codebook.json",
                    "scripts/experimental/codepack_recovery/core/oracle_codebook.py",
                ],
            )
        )

    payload = {
        "schema_version": "v1.0.0",
        "codebook_id": "recovered-codepack-archive-20260409",
        "created_at_utc": _utc_now(),
        "lookup": {"ssot_locked": True, "entries": lookup_entries},
        "training": {"enabled": False, "records": []},
        "hybrid_experiment": {
            "enabled": False,
            "quaternion_transition_enabled": False,
            "threshold_gate_enabled": False,
            "params": {"threshold_t": None, "decay_d": None, "gain_g": None},
        },
        "governance": {
            "literal_restoration_rate_required": 100.0,
            "off_by_default_policy": True,
            "promotion_rules": {
                "require_min_recall_non_degradation": True,
                "require_brier_non_degradation": True,
                "require_ci_stability": True,
            },
        },
        "fact_safe_meta": {
            "source_origin": "F:/workspace_archive/from_C_workspace_temp_20260324",
            "mapping_policy": "best-effort recovered mapping; requires promotion review before production",
            "tags": ["FACT", "HYPO"],
        },
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(OUT), "lookup_entries": len(lookup_entries)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

