# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.8, K:0.3, M:0.3}
# Balance: 93
# Purpose: Produce Track A policy floor decision artifact (keep vs adjust).
# Keywords: track_a, policy, floor, decision, commercialization
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ALIGN = ROOT / "docs" / "final" / "artifacts" / "track_a_gate_alignment_v1.json"
OUT = ROOT / "docs" / "final" / "artifacts" / "track_a_policy_floor_decision_v1.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--alignment", type=Path, default=ALIGN)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    align_path = args.alignment if args.alignment.is_absolute() else ROOT / args.alignment
    align = _load(align_path)
    floors = align.get("floors", {})
    sweeps = align.get("sweep_decisions", {})

    policy_floor = float(floors.get("policy_floor", 0.49))
    runtime_saving = float(floors.get("runtime_active_saving", 0.0))
    policy_ok = bool(floors.get("policy_floor_ok_now", False))

    relaxed = (sweeps.get("relaxed_floor_046") or {}).get("recommended") or {}
    aligned = (sweeps.get("aligned_floor_runtime") or {}).get("recommended") or {}

    option_keep = {
        "id": "OPTION_A_KEEP_POLICY_FLOOR_049",
        "description": "Keep commercialization floor at 0.49 and hold baseline until engine improves saving.",
        "pros": [
            "Maintains strict commercialization claim consistency.",
            "Avoids policy/message drift between KPI docs and runtime.",
        ],
        "cons": [
            "Blocks near-term promotion despite quality improvements.",
        ],
        "evidence": {
            "runtime_saving": runtime_saving,
            "policy_floor": policy_floor,
            "policy_floor_ok_now": policy_ok,
        },
    }

    option_adjust = {
        "id": "OPTION_B_ADJUST_POLICY_FLOOR_TO_RUNTIME",
        "description": "Lower policy floor to runtime band (~0.468) and permit promotion under revised KPI policy.",
        "pros": [
            "Aligns policy with current engine reality immediately.",
            "Enables faster promotion cadence.",
        ],
        "cons": [
            "Weakens historical 0.49 commercialization floor commitment.",
            "Requires explicit policy/communication update governance.",
        ],
        "evidence": {
            "aligned_recommended_caps": aligned.get("caps"),
            "aligned_recommended_saving": aligned.get("saving"),
            "relaxed_recommended_caps": relaxed.get("caps"),
            "relaxed_recommended_saving": relaxed.get("saving"),
        },
    }

    decision = "DECISION_KEEP_POLICY_FLOOR_049_HOLD_BASELINE"
    rationale = (
        "Policy floor 0.49 remains unmet at runtime (0.46835). "
        "Until explicit governance changes floor policy, commercialization claims stay on hold."
    )

    out_doc = {
        "schema": "track_a_policy_floor_decision_v1",
        "generated_at_utc": _now_utc(),
        "inputs": {"alignment": str(align_path)},
        "options": [option_keep, option_adjust],
        "decision": decision,
        "rationale": rationale,
        "next_action": (
            "Run engine-side saving recovery experiments under unchanged policy floor; "
            "if policy change is requested, require explicit governance approval artifact."
        ),
    }

    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "decision": decision}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
