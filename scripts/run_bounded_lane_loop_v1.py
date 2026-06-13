#!/usr/bin/env python3
"""Bounded lane loop v1 — whitelist child runners + shadow outcome only.

NOT an infinite Cursor chat loop. Does NOT enqueue todo_queue_v1 or promote Track A.

  py scripts/run_bounded_lane_loop_v1.py --dry-run
  py scripts/run_bounded_lane_loop_v1.py --pin docs/final/artifacts/fixtures/bounded_lane_pin_infra_v1.example.json

SSOT summary: reports/bounded_lane_loop_v1_latest.json
Audit append: reports/bounded_lane_loop_audit.jsonl
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PIN_SCHEMA = ROOT / "docs/final/schemas/bounded_lane_pin_v1.schema.json"
WHITELIST = ROOT / "docs/final/artifacts/bounded_lane_loop_whitelist_v1.json"
DEFAULT_PIN = ROOT / "docs/final/artifacts/fixtures/bounded_lane_pin_infra_v1.example.json"
OUT_SUMMARY = ROOT / "reports/bounded_lane_loop_v1_latest.json"
OUT_AUDIT = ROOT / "reports/bounded_lane_loop_audit.jsonl"

SHADOW_OUTCOMES = frozenset({"shadow_pass", "shadow_warning", "shadow_reject"})


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_pin(doc: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if doc.get("schema") != "bounded_lane_pin_v1":
        errors.append("schema must be bounded_lane_pin_v1")
    for key in ("lane", "next_action_one_line", "forbidden", "steps"):
        if key not in doc:
            errors.append(f"missing required field: {key}")
    steps = doc.get("steps")
    if not isinstance(steps, list) or not steps:
        errors.append("steps must be non-empty array")
    if PIN_SCHEMA.is_file():
        try:
            import jsonschema

            schema = _load_json(PIN_SCHEMA)
            jsonschema.validate(doc, schema)
        except ImportError:
            pass
        except jsonschema.ValidationError as exc:
            errors.append(f"jsonschema: {exc.message}")
    return errors


def _argv_key(runner: str, argv: list[str]) -> str:
    return f"{runner}:" + "|".join(argv)


def _matches_prefix(argv: list[str], prefix: list[str]) -> bool:
    if len(argv) < len(prefix):
        return False
    for a, b in zip(argv, prefix, strict=False):
        na = Path(a).as_posix().replace("\\", "/")
        nb = Path(b).as_posix().replace("\\", "/")
        if na != nb and not na.endswith("/" + nb) and not na.endswith(nb):
            return False
    return True


def _check_whitelist(
    whitelist: dict[str, Any], runner: str, argv: list[str]
) -> tuple[bool, str | None]:
    forbidden = whitelist.get("forbidden_argv_substrings") or []
    joined = " ".join(argv)
    for sub in forbidden:
        if sub and sub in joined:
            return False, f"forbidden_substring:{sub}"

    allowed = whitelist.get("allowed_invocations") or []
    for entry in allowed:
        if not isinstance(entry, dict):
            continue
        if entry.get("runner") != runner:
            continue
        prefix = entry.get("argv_prefix") or []
        if _matches_prefix(argv, prefix):
            return True, str(entry.get("id") or "allowed")
    return False, "not_on_whitelist"


def _build_cmd(runner: str, argv: list[str]) -> list[str]:
    if runner == "python":
        return [sys.executable, *[str(a) for a in argv]]
    if runner == "powershell":
        return [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            *[str(a) for a in argv],
        ]
    raise ValueError(f"unsupported runner: {runner}")


def _run_step(
    *,
    runner: str,
    argv: list[str],
    max_wall_seconds: int,
    cwd: Path,
) -> dict[str, Any]:
    cmd = _build_cmd(runner, argv)
    t0 = time.monotonic()
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=max_wall_seconds,
    )
    elapsed = round(time.monotonic() - t0, 3)
    return {
        "cmd": cmd,
        "exit_code": proc.returncode,
        "wall_seconds": elapsed,
        "stdout_tail": (proc.stdout or "")[-1500:],
        "stderr_tail": (proc.stderr or "")[-800:],
    }


def _shadow_outcome(
    *,
    pin_ok: bool,
    policy_violations: list[str],
    step_results: list[dict[str, Any]],
) -> str:
    if not pin_ok or policy_violations:
        return "shadow_reject"
    hard_fails = [
        s for s in step_results if s.get("exit_code") not in (0, None) and not s.get("optional")
    ]
    soft_fails = [
        s for s in step_results if s.get("exit_code") not in (0, None) and s.get("optional")
    ]
    if hard_fails:
        return "shadow_warning"
    if soft_fails:
        return "shadow_warning"
    return "shadow_pass"


def _append_audit(row: dict[str, Any]) -> None:
    OUT_AUDIT.parent.mkdir(parents=True, exist_ok=True)
    with OUT_AUDIT.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pin", type=Path, default=DEFAULT_PIN, help="bounded_lane_pin_v1 JSON")
    ap.add_argument("--whitelist", type=Path, default=WHITELIST)
    ap.add_argument("--dry-run", action="store_true", help="Validate pin + plan only")
    args = ap.parse_args()

    pin_path: Path = args.pin if args.pin.is_absolute() else ROOT / args.pin
    wl_path: Path = args.whitelist if args.whitelist.is_absolute() else ROOT / args.whitelist

    if not pin_path.is_file():
        print(f"bounded_lane_loop: missing pin {pin_path}", file=sys.stderr)
        return 1
    if not wl_path.is_file():
        print(f"bounded_lane_loop: missing whitelist {wl_path}", file=sys.stderr)
        return 1

    pin = _load_json(pin_path)
    whitelist = _load_json(wl_path)
    pin_errors = _validate_pin(pin)
    pin_ok = len(pin_errors) == 0

    max_steps = int(pin.get("max_steps_per_loop") or 3)
    max_loop_wall = int(pin.get("max_wall_seconds_per_loop") or 600)
    steps = list(pin.get("steps") or [])[:max_steps]

    policy_violations: list[str] = []
    planned: list[dict[str, Any]] = []

    allowed_map = {
        (str(e.get("runner")), tuple(e.get("argv_prefix") or [])): e
        for e in (whitelist.get("allowed_invocations") or [])
        if isinstance(e, dict)
    }

    for step in steps:
        if not isinstance(step, dict):
            policy_violations.append("invalid_step_shape")
            continue
        step_id = str(step.get("step_id") or "")
        runner = str(step.get("runner") or "")
        argv = [str(x) for x in (step.get("argv") or [])]
        ok, reason = _check_whitelist(whitelist, runner, argv)
        if not ok:
            policy_violations.append(f"{step_id}:{reason}")
        wall = 120
        for (_r, pref), entry in allowed_map.items():
            if runner == _r and _matches_prefix(argv, list(pref)):
                wall = int(entry.get("max_wall_seconds") or wall)
                break
        planned.append(
            {
                "step_id": step_id,
                "runner": runner,
                "argv": argv,
                "whitelist_ok": ok,
                "whitelist_reason": reason,
                "max_wall_seconds": wall,
                "optional": bool(step.get("optional")),
            }
        )

    if args.dry_run:
        payload = {
            "schema": "bounded_lane_loop_v1",
            "generated_at_utc": _utc(),
            "dry_run": True,
            "research_only": True,
            "pin_path": str(pin_path.relative_to(ROOT)).replace("\\", "/"),
            "lane": pin.get("lane"),
            "next_action_one_line": pin.get("next_action_one_line"),
            "peer_handoff_pointer": pin.get("peer_handoff_pointer"),
            "ltm_hint": pin.get("ltm_hint"),
            "pin_ok": pin_ok,
            "pin_errors": pin_errors,
            "policy_violations": policy_violations,
            "planned_steps": planned,
            "todo_queue_auto_enqueue": False,
            "track_a_promote": False,
            "shadow_only": True,
            "human_signoff_required": True,
            "outcome_class": _shadow_outcome(
                pin_ok=pin_ok,
                policy_violations=policy_violations,
                step_results=[],
            ),
            "reproduce": f"py scripts/run_bounded_lane_loop_v1.py --pin {pin_path.relative_to(ROOT)} --dry-run",
        }
        OUT_SUMMARY.parent.mkdir(parents=True, exist_ok=True)
        OUT_SUMMARY.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0 if payload["outcome_class"] != "shadow_reject" else 2

    if not pin_ok:
        print(f"bounded_lane_loop: pin invalid: {pin_errors}", file=sys.stderr)
        return 2
    if policy_violations:
        print(f"bounded_lane_loop: policy violations: {policy_violations}", file=sys.stderr)
        return 2

    loop_t0 = time.monotonic()
    step_results: list[dict[str, Any]] = []
    for plan in planned:
        if time.monotonic() - loop_t0 > max_loop_wall:
            policy_violations.append("loop_wall_budget_exceeded")
            break
        try:
            run = _run_step(
                runner=plan["runner"],
                argv=plan["argv"],
                max_wall_seconds=int(plan["max_wall_seconds"]),
                cwd=ROOT,
            )
        except subprocess.TimeoutExpired:
            run = {
                "cmd": _build_cmd(plan["runner"], plan["argv"]),
                "exit_code": 124,
                "wall_seconds": plan["max_wall_seconds"],
                "stdout_tail": "",
                "stderr_tail": "timeout",
            }
        row = {
            **plan,
            **run,
        }
        step_results.append(row)
        if run["exit_code"] != 0 and not plan.get("optional"):
            break

    outcome = _shadow_outcome(
        pin_ok=pin_ok,
        policy_violations=policy_violations,
        step_results=step_results,
    )
    if outcome not in SHADOW_OUTCOMES:
        outcome = "shadow_reject"

    summary = {
        "schema": "bounded_lane_loop_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "pin_path": str(pin_path.relative_to(ROOT)).replace("\\", "/"),
        "lane": pin.get("lane"),
        "next_action_one_line": pin.get("next_action_one_line"),
        "fact_lock_pointer": pin.get("fact_lock_pointer"),
        "peer_handoff_pointer": pin.get("peer_handoff_pointer"),
        "ltm_hint": pin.get("ltm_hint"),
        "loop_ok": outcome == "shadow_pass",
        "outcome_class": outcome,
        "shadow_only": True,
        "track_a_promote": False,
        "todo_queue_auto_enqueue": False,
        "human_signoff_required": True,
        "policy_violations": policy_violations,
        "steps": step_results,
        "reproduce": f"py scripts/run_bounded_lane_loop_v1.py --pin {pin_path.relative_to(ROOT)}",
    }

    OUT_SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    OUT_SUMMARY.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    _append_audit(
        {
            "ts_utc": summary["generated_at_utc"],
            "lane": summary["lane"],
            "outcome_class": outcome,
            "loop_ok": summary["loop_ok"],
            "step_ids": [s.get("step_id") for s in step_results],
            "pin_path": summary["pin_path"],
        }
    )

    print(json.dumps({"ok": summary["loop_ok"], "outcome_class": outcome, "out": str(OUT_SUMMARY)}, ensure_ascii=False))
    return 0 if outcome == "shadow_pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
