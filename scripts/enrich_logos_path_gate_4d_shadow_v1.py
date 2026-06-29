#!/usr/bin/env python3
"""Attach four_d_shadow from 41k audit onto path gate — gate_pass unchanged [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GATE_DEFAULT = ROOT / "reports/logos_path_verification_gate_v1_latest.json"
AUDIT_DEFAULT = ROOT / "reports/logos_41k_4d_reclassification_audit_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return {}


def enrich(gate_doc: dict[str, Any], audit_doc: dict[str, Any]) -> dict[str, Any]:
    out = dict(gate_doc)
    shadow = audit_doc.get("phase_pc_path_four_d_shadow") or {}
    summary = dict(out.get("summary") or {})
    prior_gate_pass = summary.get("gate_pass")

    out["four_d_shadow"] = {
        **shadow,
        "enriched_at_utc": _utc(),
        "does_not_affect_gate_pass": True,
        "lexicon_4d_coverage_rate": (audit_doc.get("phase_pb_lexicon_coverage") or {}).get(
            "lexicon_4d_coverage_rate"
        ),
        "phase_pa_exact_match_rate": (audit_doc.get("phase_pa_residual") or {}).get("exact_match_rate"),
    }
    summary["four_d_shadow_mean_coherence"] = shadow.get("mean_four_d_coherence")
    summary["four_d_human_review_hint_count"] = shadow.get("human_review_hint_count")
    summary["gate_pass"] = prior_gate_pass
    out["summary"] = summary
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gate", type=Path, default=GATE_DEFAULT)
    ap.add_argument("--audit", type=Path, default=AUDIT_DEFAULT)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    gate = _load(args.gate)
    audit = _load(args.audit)
    if not gate:
        print(json.dumps({"ok": False, "error": "path gate missing"}))
        return 2
    if not audit:
        print(json.dumps({"ok": False, "error": "41k 4d audit missing"}))
        return 2

    out_path = args.out or args.gate
    doc = enrich(gate, audit)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "gate_pass_unchanged": doc["summary"].get("gate_pass"),
                "mean_four_d_coherence": doc["summary"].get("four_d_shadow_mean_coherence"),
                "out": str(out_path),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
