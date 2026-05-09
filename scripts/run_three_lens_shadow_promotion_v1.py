#!/usr/bin/env python3
"""Promote shadow features to enabled using 7-run shadow history."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        s = line.strip()
        if not s:
            continue
        try:
            row = json.loads(s)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            out.append(row)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--policy-json", type=Path, default=ART / "three_lens_staged_inclusion_policy_v1.json")
    ap.add_argument("--history-jsonl", type=Path, default=ART / "three_lens_shadow_history_v1.jsonl")
    ap.add_argument("--output-json", type=Path, default=ART / "three_lens_shadow_promotion_v1_latest.json")
    ap.add_argument("--required-runs", type=int, default=7)
    ap.add_argument("--auto-bootstrap", action="store_true")
    args = ap.parse_args()

    policy_path = args.policy_json if args.policy_json.is_absolute() else ROOT / args.policy_json
    history_path = args.history_jsonl if args.history_jsonl.is_absolute() else ROOT / args.history_jsonl
    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json

    policy = _read_json(policy_path)
    rows = _read_jsonl(history_path)
    bootstrap_runs = 0

    if args.auto_bootstrap and len(rows) < args.required_runs:
        need = args.required_runs - len(rows)
        for _ in range(max(0, need)):
            cp = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ROOT / "scripts" / "Run-ThreeLensStagedFusionDaily.ps1")],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
            )
            if cp.returncode != 0:
                raise SystemExit(f"bootstrap chain failed: {cp.stderr}\n{cp.stdout}")
            cp2 = subprocess.run(
                ["py", str(ROOT / "scripts" / "append_three_lens_shadow_history_v1.py")],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
            )
            if cp2.returncode != 0:
                raise SystemExit(f"append history failed: {cp2.stderr}\n{cp2.stdout}")
            bootstrap_runs += 1
        rows = _read_jsonl(history_path)

    tail = rows[-args.required_runs :] if rows else []
    enough = len(tail) >= args.required_runs
    stable = enough and all(str(r.get("action") or "") in {"WATCH", "GO"} for r in tail)
    evidence_ok = enough and all(bool(r.get("enabled_evidence_all_present")) for r in tail)

    promoted_ids: list[str] = []
    features = policy.get("features") if isinstance(policy.get("features"), list) else []
    if stable and evidence_ok:
        for row in features:
            if not isinstance(row, dict):
                continue
            if str(row.get("status") or "").lower() != "shadow":
                continue
            ev = str(row.get("evidence_path") or "")
            ev_path = ROOT / ev if ev and ev != "N/A" else None
            if ev_path and ev_path.is_file():
                row["status"] = "enabled"
                promoted_ids.append(str(row.get("id") or "unknown"))

    policy_path.write_text(json.dumps(policy, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    payload = {
        "schema": "three_lens_shadow_promotion_v1",
        "generated_at_utc": _now(),
        "required_runs": args.required_runs,
        "history_count": len(rows),
        "bootstrap_runs": bootstrap_runs,
        "stable_gate_band": stable,
        "enabled_evidence_all_present_band": evidence_ok,
        "promoted_ids": promoted_ids,
        "decision": "PROMOTED" if promoted_ids else ("WAIT_MORE_HISTORY" if not enough else "NO_ELIGIBLE_SHADOW"),
        "policy_json": str(policy_path),
        "history_jsonl": str(history_path),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "decision": payload["decision"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
