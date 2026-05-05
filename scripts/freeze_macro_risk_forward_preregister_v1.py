#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_POLICY = ROOT / "docs" / "final" / "artifacts" / "macro_risk_warning_policy_binding_latest.json"
DEFAULT_MATRIX = ROOT / "docs" / "final" / "artifacts" / "macro_risk_warning_api_decision_action_matrix_v1.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "macro_risk_forward_preregister_lock_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return data


def _canonical(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Freeze forward-testing preregistration lock for macro risk.")
    p.add_argument("--policy-json", type=Path, default=DEFAULT_POLICY)
    p.add_argument("--matrix-json", type=Path, default=DEFAULT_MATRIX)
    p.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    p.add_argument("--model-id", default="fragility_composite_v1")
    p.add_argument("--window-label", default="live_forward_v1")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    policy_path = args.policy_json if args.policy_json.is_absolute() else (ROOT / args.policy_json)
    matrix_path = args.matrix_json if args.matrix_json.is_absolute() else (ROOT / args.matrix_json)
    out_path = args.out_json if args.out_json.is_absolute() else (ROOT / args.out_json)

    policy = _read_json(policy_path)
    matrix = _read_json(matrix_path)

    prereg_payload = {
        "schema": "macro_risk_forward_preregister_v1",
        "created_at_utc": _utc_now(),
        "model_id": args.model_id,
        "window_label": args.window_label,
        "policy_ref": {
            "path": str(policy_path.relative_to(ROOT)),
            "hash_sha256": _sha256_text(_canonical(policy)),
        },
        "decision_matrix_ref": {
            "path": str(matrix_path.relative_to(ROOT)),
            "hash_sha256": _sha256_text(_canonical(matrix)),
        },
        "fixed_evaluation_contract": {
            "decision_field": "decision_state",
            "risk_level_field": "risk_warning_level",
            "allowed_states": ["GO", "WATCH", "HOLD"],
            "no_retroactive_relabel": True,
        },
        "notes": "Preregistered lock for live forward testing. Update only with a new lock snapshot.",
    }
    prereg_hash = _sha256_text(_canonical(prereg_payload))
    doc = {
        **prereg_payload,
        "preregister_hash_sha256": prereg_hash,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"preregister_lock: PASS -> {out_path}")
    print(f"preregister_hash_sha256: {prereg_hash}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

