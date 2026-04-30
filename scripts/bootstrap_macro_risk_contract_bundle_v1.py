#!/usr/bin/env python3
"""Bootstrap macro risk contract/matrix/smoke artifacts for Track C chain."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.macro_risk_warning_api_stub import MacroRiskWarningRequest, build_macro_risk_warning_response


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def main() -> int:
    art = ROOT / "docs" / "final" / "artifacts"
    art.mkdir(parents=True, exist_ok=True)

    contract = {
        "schema": "macro_risk_warning_api_response_contract_v1",
        "generated_at_utc": _now_utc(),
        "field_contract": {
            "api_contract_version": "string",
            "schema_version": "macro_risk_warning_api_response_contract_v1",
            "request_id": "string",
            "timestamp_utc": "iso8601_utc",
            "asset_scope": "string",
            "decision_state": "GO|WATCH|HOLD|FORCE_HOLD|REDUCE_EXPOSURE",
            "risk_warning_level": "normal|elevated|high|critical",
            "confidence_band": "low|medium|high",
            "recommended_operator_posture": "maintain|watch_tighten|reduce_exposure|halt_new_entries",
            "ttl_seconds": "int",
        },
    }
    matrix = {
        "schema": "macro_risk_warning_api_decision_action_matrix_v1",
        "generated_at_utc": _now_utc(),
        "mapping": [
            {
                "decision_state": "GO",
                "recommended_operator_posture": "maintain",
                "client_action": "keep_default_exposure",
                "new_entry_policy": "allowed",
                "risk_notes": "No elevated macro risk.",
            },
            {
                "decision_state": "WATCH",
                "recommended_operator_posture": "watch_tighten",
                "client_action": "tighten_monitoring_and_reduce_leverage",
                "new_entry_policy": "restricted",
                "risk_notes": "Early warning regime.",
            },
            {
                "decision_state": "HOLD",
                "recommended_operator_posture": "watch_tighten",
                "client_action": "pause_new_entries",
                "new_entry_policy": "blocked",
                "risk_notes": "Insufficient conviction.",
            },
            {
                "decision_state": "REDUCE_EXPOSURE",
                "recommended_operator_posture": "reduce_exposure",
                "client_action": "reduce_exposure",
                "new_entry_policy": "blocked",
                "risk_notes": "High risk regime.",
            },
            {
                "decision_state": "FORCE_HOLD",
                "recommended_operator_posture": "halt_new_entries",
                "client_action": "force_hold_all_new_entries",
                "new_entry_policy": "blocked",
                "risk_notes": "Critical risk regime.",
            },
        ],
        "fallback_policy": {
            "client_action": "use_internal_safe_defaults_and_escalate",
            "new_entry_policy": "restricted",
            "operator_notification_required": True,
        },
    }

    smoke_req = MacroRiskWarningRequest(
        client_request_id=f"bootstrap-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        asset_scope="BTC-USD",
        horizon="24h",
        include_evidence_ref=True,
    )
    smoke = json.loads(build_macro_risk_warning_response(smoke_req).model_dump_json())

    (art / "macro_risk_warning_api_response_contract_v1.json").write_text(
        json.dumps(contract, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (art / "macro_risk_warning_api_decision_action_matrix_v1.json").write_text(
        json.dumps(matrix, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (art / "macro_risk_warning_api_smoke_latest.json").write_text(
        json.dumps(smoke, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(str(art / "macro_risk_warning_api_response_contract_v1.json"))
    print(str(art / "macro_risk_warning_api_decision_action_matrix_v1.json"))
    print(str(art / "macro_risk_warning_api_smoke_latest.json"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

