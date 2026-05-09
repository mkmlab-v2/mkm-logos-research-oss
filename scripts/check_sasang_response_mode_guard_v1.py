from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    ap = argparse.ArgumentParser(description="Guard Sasang response mode and auto-fix to prod when drift is detected.")
    ap.add_argument(
        "--response-json",
        type=Path,
        default=root / "reports" / "sasang_rule_based_response_v1_latest.json",
    )
    ap.add_argument(
        "--policy-json",
        type=Path,
        default=root / "docs" / "final" / "artifacts" / "sasang_response_formatting_policy_v1.json",
    )
    ap.add_argument(
        "--builder-script",
        type=Path,
        default=root / "scripts" / "build_sasang_rule_based_response_v1.py",
    )
    ap.add_argument(
        "--output-json",
        type=Path,
        default=root / "reports" / "sasang_response_mode_guard_latest.json",
    )
    ap.add_argument(
        "--log-jsonl",
        type=Path,
        default=root / "reports" / "sasang_response_mode_guard_log.jsonl",
    )
    ns = ap.parse_args()

    detected_mode = "MISSING"
    drift_detected = True
    autofix_applied = False
    status = "ALERT"
    note = ""

    if ns.response_json.is_file():
        doc = _load_json(ns.response_json)
        detected_mode = str(doc.get("response_mode") or "MISSING").strip().lower() or "MISSING"
        drift_detected = detected_mode != "prod"
    else:
        note = "response_json_missing"

    if drift_detected:
        proc = subprocess.run(
            [sys.executable, str(ns.builder_script), "--response-mode", "prod"],
            cwd=str(root),
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode == 0 and ns.response_json.is_file():
            updated = _load_json(ns.response_json)
            mode_after = str(updated.get("response_mode") or "").strip().lower()
            autofix_applied = mode_after == "prod"
            drift_detected = not autofix_applied
        if proc.returncode != 0:
            note = f"autofix_failed:{(proc.stderr or proc.stdout).strip()[-240:]}"
    if not drift_detected:
        status = "PASS"
        if not note:
            note = "prod_mode_confirmed"

    payload = {
        "schema": "sasang_response_mode_guard_v1",
        "generated_at_utc": _utc_now(),
        "status": status,
        "response_json": str(ns.response_json),
        "policy_json": str(ns.policy_json),
        "detected_mode": detected_mode,
        "drift_detected": drift_detected,
        "autofix_applied": autofix_applied,
        "note": note,
    }
    ns.output_json.parent.mkdir(parents=True, exist_ok=True)
    ns.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _append_jsonl(ns.log_jsonl, payload)
    print(f"WROTE: {ns.output_json}")
    print(f"STATUS={status} autofix={autofix_applied}")
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
