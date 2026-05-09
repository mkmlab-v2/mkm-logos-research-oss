from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run non-live execution gate rehearsal matrix.")
    p.add_argument(
        "--output-json",
        default="reports/execution_gate_rehearsal_matrix_latest.json",
        help="Output JSON report path.",
    )
    p.add_argument(
        "--output-md",
        default="reports/execution_gate_rehearsal_matrix_latest.md",
        help="Output markdown report path.",
    )
    return p.parse_args()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _run_gate(workspace: Path, gate_script: Path, intent: dict[str, Any], governance_status: str) -> dict[str, Any]:
    tmp_dir = workspace / "reports" / "_tmp_rehearsal"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    req_id = str(intent.get("request_id") or f"req-{int(datetime.now(timezone.utc).timestamp())}")

    gov_path = tmp_dir / f"{req_id}_gov.json"
    sec_path = tmp_dir / f"{req_id}_sec.json"
    ops_path = tmp_dir / f"{req_id}_ops.json"
    intent_path = tmp_dir / f"{req_id}_intent.json"
    decision_path = tmp_dir / f"{req_id}_decision.json"

    _write_json(gov_path, {"status": governance_status})
    _write_json(sec_path, {"status": "GREEN"})
    _write_json(ops_path, {"mode": "NORMAL"})
    _write_json(intent_path, intent)

    cmd = [
        sys.executable,
        str(gate_script),
        "--governance-path",
        str(gov_path),
        "--security-status-path",
        str(sec_path),
        "--ops-status-path",
        str(ops_path),
        "--intent-path",
        str(intent_path),
        "--output-path",
        str(decision_path),
    ]
    proc = subprocess.run(cmd, cwd=str(workspace), capture_output=True, text=True)
    decision: dict[str, Any] = {}
    if decision_path.exists():
        decision = json.loads(decision_path.read_text(encoding="utf-8"))
    return {
        "request_id": req_id,
        "intent_type": intent.get("intent_type", ""),
        "governance_status": governance_status,
        "exit_code": proc.returncode,
        "stdout": (proc.stdout or "").strip(),
        "stderr": (proc.stderr or "").strip(),
        "decision": decision.get("decision", "UNKNOWN"),
        "allow_order": decision.get("allow_order", False),
        "reasons": decision.get("reasons", []),
    }


def build_md(report: dict[str, Any]) -> str:
    lines = [
        "# Execution Gate Rehearsal Matrix",
        "",
        f"- generated_at_utc: `{report['generated_at_utc']}`",
        f"- total_cases: `{report['total_cases']}`",
        f"- pass_cases: `{report['pass_cases']}`",
        f"- fail_cases: `{report['fail_cases']}`",
        "",
        "## Cases",
    ]
    for c in report["cases"]:
        status = "PASS" if c["ok"] else "FAIL"
        lines.append(
            f"- `{status}` `{c['intent_type']}` ({c['request_id']}): expected=`{c['expected_decision']}` actual=`{c['actual_decision']}` reasons=`{','.join(c['reasons'])}`"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    workspace = Path(__file__).resolve().parents[1]
    gate_script = workspace / "scripts" / "run_execution_gate_v1.py"
    if not gate_script.exists():
        print(f"missing_gate_script={gate_script}")
        return 2

    cases = [
        {
            "expected": "ALLOW",
            "governance": "GREEN",
            "intent": {
                "request_id": "reh-open-long-allow",
                "symbol": "BTCUSDT",
                "side": "BUY",
                "qty": 0.001,
                "leverage": 1,
                "intent_type": "open_long_position",
            },
        },
        {
            "expected": "ALLOW",
            "governance": "GREEN",
            "intent": {
                "request_id": "reh-open-short-allow",
                "symbol": "BTCUSDT",
                "side": "SELL",
                "qty": 0.001,
                "leverage": 1,
                "intent_type": "open_short_position",
            },
        },
        {
            "expected": "BLOCK",
            "governance": "GREEN",
            "intent": {
                "request_id": "reh-close-block-leverage",
                "symbol": "BTCUSDT",
                "side": "SELL",
                "qty": 0.001,
                "leverage": 2,
                "intent_type": "close_position",
            },
        },
        {
            "expected": "BLOCK",
            "governance": "RED",
            "intent": {
                "request_id": "reh-protective-block-governance",
                "symbol": "BTCUSDT",
                "side": "REDUCE_ONLY_PROTECTIVE",
                "qty": 0.001,
                "intent_type": "protective_orders",
            },
        },
    ]

    out_cases: list[dict[str, Any]] = []
    for c in cases:
        run = _run_gate(workspace, gate_script, c["intent"], c["governance"])
        ok = run["decision"] == c["expected"]
        out_cases.append(
            {
                "request_id": run["request_id"],
                "intent_type": run["intent_type"],
                "expected_decision": c["expected"],
                "actual_decision": run["decision"],
                "ok": ok,
                "reasons": run["reasons"],
                "exit_code": run["exit_code"],
            }
        )

    pass_count = sum(1 for c in out_cases if c["ok"])
    report = {
        "schema": "execution_gate_rehearsal_matrix_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "total_cases": len(out_cases),
        "pass_cases": pass_count,
        "fail_cases": len(out_cases) - pass_count,
        "cases": out_cases,
    }

    out_json = Path(args.output_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out_md = Path(args.output_md)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(build_md(report), encoding="utf-8")
    print(f"execution_gate_rehearsal_written={out_json.as_posix()}")
    return 0 if report["fail_cases"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
