#!/usr/bin/env python3
"""Rebuild general_prophecy_evolution_health_latest.json + append history JSONL."""

from __future__ import annotations

import argparse
import json
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs/final/artifacts/general_prophecy_evolution_health_latest.json"
DEFAULT_HISTORY = ROOT / "docs/final/artifacts/general_prophecy_evolution_health_history_v1.jsonl"
WEEKLY_TASK = "\\GeneralProphecyHoldoutEvolutionWeeklyV1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        o = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None
    return o if isinstance(o, dict) else None


def _tail_history(path: Path, *, max_lines: int = 200) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()][-max_lines:]
    out: list[dict[str, Any]] = []
    for ln in lines:
        try:
            out.append(json.loads(ln))
        except json.JSONDecodeError:
            continue
    return out


def _query_task(task_name: str) -> dict[str, Any]:
    cp = subprocess.run(
        ["schtasks", "/Query", "/TN", task_name, "/V", "/FO", "LIST"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    if cp.returncode != 0:
        return {"exists": False, "enabled": False, "last_result": None, "query_ok": False}
    raw = (cp.stdout or "") + (cp.stderr or "")
    enabled = "Disabled" not in raw or "Scheduled Task State:" in raw and "Ready" in raw
    last_result = ""
    for line in raw.splitlines():
        if line.strip().startswith("Last Result:"):
            last_result = line.split(":", 1)[1].strip()
            break
    return {
        "exists": True,
        "enabled": enabled,
        "last_result": last_result or None,
        "query_ok": True,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--history-jsonl", type=Path, default=DEFAULT_HISTORY)
    ap.add_argument("--weekly-task-name", default=WEEKLY_TASK)
    args = ap.parse_args()

    ablation_path = ROOT / "docs/final/artifacts/general_prophecy_holdout_evolution_ablation_latest.json"
    myeongni_path = ROOT / "docs/final/artifacts/mkm_myeongni_response_v2_latest.json"
    ablation = _read_json(ablation_path)
    myeongni = _read_json(myeongni_path)

    ablation_schema_ok = bool(ablation and str(ablation.get("schema") or "").startswith("general_prophecy_holdout"))
    ablation_mode_ok = ablation.get("mode") == "proposal_only_no_auto_apply" if ablation else False
    candidate_rows = 0
    if ablation and isinstance(ablation.get("candidate_results"), list):
        candidate_rows = len(ablation["candidate_results"])
    recommended_id = ablation.get("recommended_candidate_id") if ablation else None
    if recommended_id is None and ablation and isinstance(ablation.get("recommended"), dict):
        recommended_id = ablation["recommended"].get("candidate_id")

    myeongni_schema_ok = bool(myeongni and str(myeongni.get("schema") or "").startswith("mkm_myeongni"))
    myeongni_track_ok = myeongni.get("track") in (None, "B", "OBSERVATION_ONLY") if myeongni else False
    decision = str(myeongni.get("decision") or "HOLD") if myeongni else "MISSING"
    myeongni_decision_ok = decision in ("HOLD", "WATCH", "REDUCE", "GO")
    direction_override = myeongni.get("direction_override_allowed") if myeongni else None
    direction_override_ok = direction_override is False or direction_override is None

    task = _query_task(args.weekly_task_name)
    history = _tail_history(args.history_jsonl)
    decision_counts: Counter[str] = Counter()
    ablation_rec_counts: Counter[str] = Counter()
    watch_streak = 0
    for row in reversed(history):
        if not decision_counts and isinstance(row.get("myeongni_v2_decision"), str):
            decision_counts[row["myeongni_v2_decision"]] += 1
        rid = row.get("ablation_recommended_candidate_id")
        if isinstance(rid, str):
            ablation_rec_counts[rid] += 1
    for row in reversed(history[-20:]):
        if row.get("myeongni_v2_decision") == "WATCH":
            watch_streak += 1
        else:
            break
    decision_counts[decision] += 1
    if recommended_id:
        ablation_rec_counts[str(recommended_id)] += 1

    all_pass = (
        ablation_schema_ok
        and ablation_mode_ok
        and myeongni_schema_ok
        and myeongni_track_ok
        and myeongni_decision_ok
        and direction_override_ok
        and task.get("query_ok", False)
    )

    out: dict[str, Any] = {
        "schema": "general_prophecy_evolution_health_v1",
        "checked_at_utc": _utc_now(),
        "ablation_artifact_path": str(ablation_path.resolve()),
        "ablation_schema_ok": ablation_schema_ok,
        "ablation_mode_ok": ablation_mode_ok,
        "ablation_candidate_rows": candidate_rows,
        "ablation_recommended_candidate_id": recommended_id,
        "myeongni_v2_artifact_path": str(myeongni_path.resolve()),
        "myeongni_v2_schema_ok": myeongni_schema_ok,
        "myeongni_v2_track_ok": myeongni_track_ok,
        "myeongni_v2_decision": decision,
        "myeongni_v2_decision_ok": myeongni_decision_ok,
        "myeongni_v2_direction_override_allowed": direction_override,
        "myeongni_v2_direction_override_ok": direction_override_ok,
        "evolution_weekly_task_name": args.weekly_task_name,
        "evolution_weekly_task_exists": task.get("exists", False),
        "evolution_weekly_task_enabled": task.get("enabled", False),
        "evolution_weekly_task_last_result": task.get("last_result"),
        "evolution_health_history_path": str(args.history_jsonl.resolve()),
        "evolution_health_history_size": len(history) + 1,
        "myeongni_v2_decision_counts": dict(decision_counts),
        "ablation_recommended_candidate_id_counts": dict(ablation_rec_counts),
        "myeongni_v2_watch_streak": watch_streak,
        "all_pass": all_pass,
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    hist_row = {
        "schema": "general_prophecy_evolution_health_history_row_v1",
        "checked_at_utc": out["checked_at_utc"],
        "myeongni_v2_decision": decision,
        "ablation_recommended_candidate_id": recommended_id,
        "all_pass": all_pass,
    }
    args.history_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.history_jsonl.open("a", encoding="utf-8") as f:
        f.write(json.dumps(hist_row, ensure_ascii=False) + "\n")

    print(json.dumps({"all_pass": all_pass, "out": str(args.out_json.resolve())}, ensure_ascii=False))
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
