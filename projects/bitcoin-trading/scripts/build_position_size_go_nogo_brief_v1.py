#!/usr/bin/env python3
"""Build one-line GO/NO-GO brief from promotion gate + coverage status."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path("/opt/bitcoin-trading-live")
ART = ROOT / "docs" / "final" / "artifacts"
OUT_JSON = ART / "position_size_go_nogo_brief_latest.json"
OUT_MD = ART / "position_size_go_nogo_brief_latest.md"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    gate = _read_json(ART / "position_size_promotion_gate_latest.json")
    cov = _read_json(Path("/opt/bitcoin-trading/docs/final/artifacts/protective_order_coverage_latest.json"))

    decision = str(gate.get("decision") or "unknown")
    gates = gate.get("gates") if isinstance(gate.get("gates"), dict) else {}
    coverage_ok = bool(cov.get("ok")) or str(cov.get("status") or "") == "no_open_position"
    go = decision == "promote" and coverage_ok

    summary = {
        "schema": "position_size_go_nogo_brief_v1",
        "generated_at_utc": _utc_now(),
        "go": go,
        "decision": "GO" if go else "NO-GO",
        "inputs": {
            "promotion_decision": decision,
            "sample_gate": bool(gates.get("sample_gate", False)),
            "expectancy_gate": bool(gates.get("expectancy_gate", False)),
            "loss_streak_gate": bool(gates.get("loss_streak_gate", False)),
            "coverage_status": cov.get("status"),
            "coverage_ok": coverage_ok,
        },
        "one_liner": (
            "GO: 0.003 증액 가능"
            if go
            else "NO-GO: 0.001 유지"
        ),
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT_MD.write_text(
        "\n".join(
            [
                "# Position Size GO/NO-GO",
                "",
                f"- generated_at_utc: {summary['generated_at_utc']}",
                f"- decision: **{summary['decision']}**",
                f"- one_liner: {summary['one_liner']}",
                (
                    f"- gates: sample={summary['inputs']['sample_gate']}, "
                    f"expectancy={summary['inputs']['expectancy_gate']}, "
                    f"loss_streak={summary['inputs']['loss_streak_gate']}, "
                    f"coverage={summary['inputs']['coverage_status']}"
                ),
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(summary["one_liner"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
