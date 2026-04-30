from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build single status pointer from MKM AI v2 promotion lock."
    )
    parser.add_argument("--workspace-root", default="C:/workspace")
    return parser.parse_args()


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def main() -> int:
    args = _parse_args()
    root = Path(args.workspace_root)

    lock_path = root / "docs" / "final" / "artifacts" / "mkm_ai_v2_final_promotion_lock_latest.json"
    decision_path = root / "docs" / "final" / "artifacts" / "mkm_ai_v2_promotion_decision_latest.json"
    out_path = root / "docs" / "final" / "artifacts" / "mkm_ai_status_pointer_latest.json"

    lock = _read_json(lock_path)
    decision = _read_json(decision_path)

    status = str(lock.get("status", "HOLD_OPERATIONAL_V1"))
    label = str(lock.get("system_label", "MKM AI Cursor operational profile"))
    gate_summary = lock.get("gate_summary", {})

    payload = {
        "schema": "mkm_ai_status_pointer_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": status,
        "system_label": label,
        "is_final": status == "APPROVED_FINAL_V2",
        "decision": decision.get("decision"),
        "promotion_ready": decision.get("promotion_ready"),
        "weekly_pass_rate_percent": gate_summary.get("weekly_pass_rate_percent"),
        "weekly_sample_count": gate_summary.get("weekly_sample_count"),
        "evidence": {
            "promotion_lock": str(lock_path).replace("\\", "/"),
            "promotion_decision": str(decision_path).replace("\\", "/"),
        },
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"status pointer written: {out_path}")
    print(f"status={status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
