#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_PRESETS = ROOT / "docs" / "final" / "artifacts" / "myeongni_conflict_arbitration_presets_v1_latest.json"
DEFAULT_POLICY = ROOT / "data" / "myeongni" / "myeongni_conflict_arbitration_v1.json"
DEFAULT_AUDIT = ROOT / "reports" / "myeongni_conflict_arbitration_preset_apply_log.jsonl"
DEFAULT_RUNTIME = ROOT / "reports" / "myeongni_conflict_arbitration_runtime_mode_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _apply_patch(policy: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    out = json.loads(json.dumps(policy))
    out["arbitration_rules"]["rule_1_eokbu_vs_jogoo"]["threshold"]["jogoo_imbalance_abs"] = patch["rule_1_eokbu_vs_jogoo.threshold.jogoo_imbalance_abs"]
    out["arbitration_rules"]["rule_2_surface_vs_jijangan"]["weights"]["jijangan_root"] = patch["rule_2_surface_vs_jijangan.weights.jijangan_root"]
    out["arbitration_rules"]["rule_3_gyukguk_vs_4d_vector"]["stability_band"] = patch["rule_3_gyukguk_vs_4d_vector.stability_band"]
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Apply myeongni arbitration preset with audit and fail-closed verification.")
    ap.add_argument("--preset", choices=("conservative", "neutral", "aggressive"), default="neutral")
    ap.add_argument("--presets-json", type=Path, default=DEFAULT_PRESETS)
    ap.add_argument("--policy-json", type=Path, default=DEFAULT_POLICY)
    ap.add_argument("--audit-log-jsonl", type=Path, default=DEFAULT_AUDIT)
    ap.add_argument("--runtime-stamp-json", type=Path, default=DEFAULT_RUNTIME)
    ap.add_argument("--actor", default="cursor_agent")
    args = ap.parse_args()

    presets_path = args.presets_json if args.presets_json.is_absolute() else ROOT / args.presets_json
    policy_path = args.policy_json if args.policy_json.is_absolute() else ROOT / args.policy_json
    audit_path = args.audit_log_jsonl if args.audit_log_jsonl.is_absolute() else ROOT / args.audit_log_jsonl
    runtime_path = args.runtime_stamp_json if args.runtime_stamp_json.is_absolute() else ROOT / args.runtime_stamp_json

    presets_doc = _read_json(presets_path)
    presets = {p.get("preset_name"): p for p in (presets_doc.get("presets") or [])}
    if args.preset not in presets:
        raise SystemExit(f"preset not found: {args.preset}")

    before_text = policy_path.read_text(encoding="utf-8")
    before_hash = _sha256_text(before_text)
    before = json.loads(before_text)
    patch = presets[args.preset]["recommended_policy_patch"]
    after = _apply_patch(before, patch)
    after_text = json.dumps(after, ensure_ascii=False, indent=2) + "\n"
    after_hash = _sha256_text(after_text)
    policy_path.write_text(after_text, encoding="utf-8")

    verify_cmd = [
        sys.executable,
        str(ROOT / "scripts" / "verify_myeongni_conflict_arbitration_edgecases_v1.py"),
        "--policy-json",
        str(policy_path),
    ]
    cp = subprocess.run(verify_cmd, cwd=str(ROOT), capture_output=True, text=True)
    verification_pass = cp.returncode == 0

    event = {
        "ts_utc": _now(),
        "schema": "myeongni_conflict_arbitration_preset_apply_log_v1",
        "preset": args.preset,
        "actor": args.actor,
        "old_hash": before_hash,
        "new_hash": after_hash,
        "verification_pass": verification_pass,
        "verify_exit_code": cp.returncode,
    }

    if not verification_pass:
        # Fail-closed: rollback to neutral preset
        neutral_patch = presets["neutral"]["recommended_policy_patch"]
        rollback = _apply_patch(after, neutral_patch)
        rollback_text = json.dumps(rollback, ensure_ascii=False, indent=2) + "\n"
        policy_path.write_text(rollback_text, encoding="utf-8")
        event["reason"] = "edgecase_verification_failed_rolled_back_to_neutral"
    else:
        event["reason"] = "applied_and_verified"

    audit_path.parent.mkdir(parents=True, exist_ok=True)
    with audit_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")

    runtime_doc = {
        "schema": "myeongni_conflict_arbitration_runtime_mode_v1",
        "generated_at_utc": _now(),
        "mode": args.preset if verification_pass else "neutral",
        "policy_path": str(policy_path.resolve()),
        "policy_hash": _sha256_text(policy_path.read_text(encoding="utf-8")),
        "verification_pass": verification_pass,
        "actor": args.actor,
    }
    runtime_path.parent.mkdir(parents=True, exist_ok=True)
    runtime_path.write_text(json.dumps(runtime_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": verification_pass,
                "applied_preset": args.preset,
                "effective_mode": runtime_doc["mode"],
                "audit_log": str(audit_path),
                "runtime_stamp": str(runtime_path),
            },
            ensure_ascii=False,
        )
    )
    return 0 if verification_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
