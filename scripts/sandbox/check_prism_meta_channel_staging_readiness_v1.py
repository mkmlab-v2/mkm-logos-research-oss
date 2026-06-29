#!/usr/bin/env python3
"""[HYPO] Mechanical + human readiness for Prism meta sidecar B-track staging."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CHECKLIST = ROOT / "experiments/no_guard_limit_test/prism_meta_channel_staging_checklist_v1.json"
DEFAULT_OUT = ROOT / "experiments/no_guard_limit_test/results/prism_meta_channel_staging_readiness_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _get_field(doc: dict[str, Any], dotted: str) -> Any:
    cur: Any = doc
    for part in dotted.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def _eval_artifact_gate(gate: dict[str, Any]) -> dict[str, Any]:
    rel = str(gate.get("path") or "")
    path = ROOT / rel
    doc = _read(path)
    field = str(gate.get("field") or "")
    actual = _get_field(doc, field) if doc else None
    status = "FAIL"
    detail = ""
    if not doc:
        detail = "missing artifact"
    elif "expect" in gate:
        status = "PASS" if actual == gate["expect"] else "FAIL"
        detail = f"actual={actual!r} expect={gate['expect']!r}"
    elif "min" in gate:
        try:
            ok = float(actual) >= float(gate["min"])
        except (TypeError, ValueError):
            ok = False
        status = "PASS" if ok else "FAIL"
        detail = f"actual={actual!r} min={gate['min']!r}"
    else:
        detail = "no expect/min rule"
    return {
        "id": gate.get("id"),
        "status": status,
        "path": rel,
        "field": field,
        "detail": detail,
    }


def _eval_signoff(checklist: dict[str, Any]) -> dict[str, Any]:
    hs = checklist.get("human_signoff") or {}
    rel = str(hs.get("signoff_path") or "")
    path = ROOT / rel
    doc = _read(path)
    if not doc:
        return {
            "present": False,
            "status": "PENDING",
            "path": rel,
            "detail": "signoff file absent — copy from example and approve locally",
        }
    approved = bool(doc.get(str(hs.get("attestation_key") or "prism_meta_channel_staging_approved")))
    attest = doc.get("attestations") or {}
    required = list(hs.get("attestations_required") or [])
    missing = [k for k in required if attest.get(k) is not True]
    if approved and not missing:
        return {"present": True, "status": "PASS", "path": rel, "detail": "human sign-off OK"}
    if doc and not approved:
        return {"present": True, "status": "PENDING", "path": rel, "detail": "present but not approved"}
    return {
        "present": True,
        "status": "PENDING",
        "path": rel,
        "detail": f"missing attestations: {missing}",
    }


def evaluate_readiness(
    checklist: dict[str, Any],
    *,
    run_pytest: bool = False,
) -> dict[str, Any]:
    signoff = _eval_signoff(checklist)
    signoff_pass = signoff.get("status") == "PASS"

    gates: list[dict[str, Any]] = []
    base_fail: list[str] = []
    post_fail: list[str] = []
    for gate in checklist.get("artifact_gates") or []:
        if gate.get("required_after_human_signoff") and not signoff_pass:
            gates.append(
                {
                    "id": gate.get("id"),
                    "status": "SKIP",
                    "path": gate.get("path"),
                    "field": gate.get("field"),
                    "detail": "awaiting human sign-off",
                }
            )
            continue
        result = _eval_artifact_gate(gate)
        gates.append(result)
        if result.get("status") != "PASS":
            if gate.get("required_after_human_signoff"):
                post_fail.append(str(result.get("id")))
            else:
                base_fail.append(str(result.get("id")))

    pytest_ok: bool | None = None
    if run_pytest:
        tests = list(checklist.get("pytest_smoke") or [])
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", *tests, "-q", "--tb=no"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        pytest_ok = proc.returncode == 0

    mechanical_ok = not base_fail
    staging_enable_ok = mechanical_ok and signoff_pass and not post_fail
    if pytest_ok is False:
        staging_enable_ok = False

    return {
        "schema": "prism_meta_channel_staging_readiness_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "track_wall": "not_track_a_promotion",
        "env_flag": checklist.get("env_flag"),
        "env_default": checklist.get("env_default"),
        "rollback_ko": checklist.get("rollback_ko"),
        "mechanical_ok": mechanical_ok,
        "staging_enable_ok": staging_enable_ok,
        "human_signoff": signoff,
        "artifact_gates": gates,
        "mechanical_failures": base_fail,
        "post_signoff_failures": post_fail,
        "pytest_smoke_ok": pytest_ok,
        "boundary_ack": "staging_enable_ok ≠ Track A promotion; env flag local/staging only.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Prism meta channel staging readiness gate.")
    ap.add_argument("--checklist", default=str(DEFAULT_CHECKLIST))
    ap.add_argument("--out-json", default=str(DEFAULT_OUT))
    ap.add_argument("--run-pytest", action="store_true")
    ap.add_argument("--strict", action="store_true", help="Exit 1 unless mechanical_ok")
    ap.add_argument(
        "--require-staging-enable",
        action="store_true",
        help="Exit 1 unless staging_enable_ok (includes human sign-off)",
    )
    args = ap.parse_args()

    checklist_path = Path(args.checklist)
    if not checklist_path.is_absolute():
        checklist_path = ROOT / checklist_path
    checklist = _read(checklist_path)
    if not checklist:
        raise SystemExit(f"missing checklist: {checklist_path}")

    doc = evaluate_readiness(checklist, run_pytest=bool(args.run_pytest))
    out = Path(args.out_json)
    if not out.is_absolute():
        out = ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out))
    print(
        f"mechanical_ok={doc.get('mechanical_ok')} "
        f"staging_enable_ok={doc.get('staging_enable_ok')} "
        f"signoff={ (doc.get('human_signoff') or {}).get('status') }"
    )

    if args.require_staging_enable and not doc.get("staging_enable_ok"):
        return 1
    if args.strict and not doc.get("mechanical_ok"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
