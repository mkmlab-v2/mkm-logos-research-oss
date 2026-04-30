from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sync final promotion lock from latest promotion decision artifact."
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

    decision_path = root / "docs" / "final" / "artifacts" / "mkm_ai_v2_promotion_decision_latest.json"
    weekly_path = root / "docs" / "final" / "artifacts" / "mkm_ai_v2_weekly_readiness_report_latest.json"
    readiness_log_path = root / "reports" / "mkm_ai_v2_readiness_log.jsonl"
    lock_path = root / "docs" / "final" / "artifacts" / "mkm_ai_v2_final_promotion_lock_latest.json"

    decision = _read_json(decision_path)
    decision_label = str(decision.get("decision", "HOLD_OPERATIONAL_V1"))
    promotion_ready = bool(decision.get("promotion_ready", False))
    metrics = decision.get("metrics", {}) if isinstance(decision.get("metrics"), dict) else {}

    approved = decision_label == "GO_FINAL_V2" and promotion_ready
    status = "APPROVED_FINAL_V2" if approved else "HOLD_OPERATIONAL_V1"
    system_label = "MKM AI v2.0 (Final)" if approved else "MKM AI Cursor operational profile"

    payload = {
        "schema": "mkm_ai_v2_final_promotion_lock_v2",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": status,
        "system_label": system_label,
        "evidence": {
            "promotion_decision": str(decision_path).replace("\\", "/"),
            "weekly_readiness_report": str(weekly_path).replace("\\", "/"),
            "daily_readiness_log": str(readiness_log_path).replace("\\", "/"),
        },
        "gate_summary": {
            "decision": decision_label,
            "promotion_ready": promotion_ready,
            "weekly_pass_rate_percent": metrics.get("weekly_pass_rate_percent"),
            "weekly_sample_count": metrics.get("weekly_sample_count"),
        },
        "policy_note": "Lock is synced from latest promotion decision. If decision is not GO_FINAL_V2, system label is held at operational profile.",
    }

    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"promotion lock synced: {lock_path}")
    print(f"status={status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
