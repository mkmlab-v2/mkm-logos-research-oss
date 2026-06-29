#!/usr/bin/env python3
"""Build TKM encounter_sequence post-P68 breakpoint passive drift observation [HYPO]."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/tkm_encounter_sequence_post_breakpoint_passive_drift_observation_v1_latest.json"
ARTIFACT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_post_breakpoint_passive_drift_observation_v1_latest.json"
HISTORY = ROOT / "reports/tkm_encounter_sequence_post_breakpoint_passive_drift_history_v1.jsonl"

P68_GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p68_gate_v1_latest.json"
STACK_CLOSURE = ROOT / "reports/tkm_encounter_sequence_ultra_grand_stack_stack_closure_v1_latest.json"
WEEKLY = ROOT / "reports/encounter_sequence_weekly_report_v1_latest.json"
PASSIVE = ROOT / "reports/tkm_encounter_sequence_passive_observation_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _last_history() -> dict[str, Any]:
    if not HISTORY.is_file():
        return {}
    last = ""
    for line in HISTORY.read_text(encoding="utf-8").splitlines():
        if line.strip():
            last = line
    if not last:
        return {}
    try:
        return json.loads(last)
    except json.JSONDecodeError:
        return {}


def _snapshot(stack: dict[str, Any], weekly: dict[str, Any], passive: dict[str, Any]) -> dict[str, Any]:
    ugssc = weekly.get("ultra_grand_stack_stack_closure_kpi") if isinstance(
        weekly.get("ultra_grand_stack_stack_closure_kpi"), dict
    ) else {}
    return {
        "gates_ok_count": stack.get("gates_ok_count"),
        "ultra_grand_stack_breakpoint_freeze": stack.get("ultra_grand_stack_breakpoint_freeze"),
        "weekly_version": weekly.get("version"),
        "weekly_ok": weekly.get("weekly_ok"),
        "ultra_grand_stack_stack_closure_headline_ok": ugssc.get("ultra_grand_stack_stack_closure_headline_ok"),
        "passive_observation_ok": passive.get("observation_ok"),
        "weekly_task_ready": passive.get("weekly_task_ready"),
        "curated_reviewed_count": stack.get("curated_reviewed_count"),
    }


def build(*, append_history: bool = True) -> dict[str, Any]:
    p68 = _load(P68_GATE)
    stack = _load(STACK_CLOSURE)
    weekly = _load(WEEKLY)
    passive = _load(PASSIVE)
    prev = _last_history()
    snap = _snapshot(stack, weekly, passive)

    drift_regression = False
    if prev:
        prev_snap = prev.get("snapshot") if isinstance(prev.get("snapshot"), dict) else {}
        for key in ("gates_ok_count", "ultra_grand_stack_breakpoint_freeze", "weekly_ok", "passive_observation_ok"):
            if prev_snap.get(key) is not None and prev_snap.get(key) != snap.get(key):
                drift_regression = True

    observation_ok = (
        p68.get("gate_ok") is True
        and stack.get("ultra_grand_stack_stack_closure_ok") is True
        and stack.get("ultra_grand_stack_breakpoint_freeze") is True
        and weekly.get("weekly_ok") is True
        and passive.get("observation_ok") is True
        and passive.get("weekly_task_ready") is True
        and snap.get("ultra_grand_stack_stack_closure_headline_ok") is True
        and not drift_regression
        and p68.get("send_gate") == "HOLD"
    )

    doc = {
        "schema": "tkm_encounter_sequence_post_breakpoint_passive_drift_observation_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "domain_lane": "tkm_korean_han_medicine",
        "send_gate": "HOLD",
        "non_gating": True,
        "research_only": True,
        "observation_ok": observation_ok,
        "p68_gate_ok": p68.get("gate_ok"),
        "ultra_grand_stack_stack_closure_ok": stack.get("ultra_grand_stack_stack_closure_ok"),
        "ultra_grand_stack_breakpoint_freeze": stack.get("ultra_grand_stack_breakpoint_freeze"),
        "passive_observation_ok": passive.get("observation_ok"),
        "weekly_task_ready": passive.get("weekly_task_ready"),
        "drift_regression_detected": drift_regression,
        "snapshot": snap,
        "previous_snapshot": prev.get("snapshot") if prev else None,
        "tier_inflation_forbidden": True,
        "auto_training_forbidden": True,
        "note_ko": "Post-P68 breakpoint passive drift observation [HYPO][NON_GATING]; P69+ tier inflation 금지.",
        "reproduce": "py scripts/build_tkm_encounter_sequence_post_breakpoint_passive_drift_observation_v1.py",
    }

    if append_history:
        HISTORY.parent.mkdir(parents=True, exist_ok=True)
        with HISTORY.open("a", encoding="utf-8") as fh:
            fh.write(
                json.dumps(
                    {
                        "generated_at_utc": doc["generated_at_utc"],
                        "observation_ok": observation_ok,
                        "drift_regression_detected": drift_regression,
                        "snapshot": snap,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )

    return doc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--no-history", action="store_true")
    ap.add_argument("--mirror-artifact", action="store_true", default=True)
    ap.add_argument("--no-mirror-artifact", action="store_false", dest="mirror_artifact")
    args = ap.parse_args()
    doc = build(append_history=not args.no_history)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.mirror_artifact:
        ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(args.out, ARTIFACT)
    print(json.dumps({"ok": doc.get("observation_ok"), "drift_regression": doc.get("drift_regression_detected")}))
    return 0 if doc.get("observation_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
