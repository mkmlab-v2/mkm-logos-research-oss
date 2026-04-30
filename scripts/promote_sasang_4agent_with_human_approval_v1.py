#!/usr/bin/env python3
"""Apply explicit human approval to sasang 4-agent promotion gate."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _safe_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--approver", required=True)
    ap.add_argument("--note", default="Human approved promotion candidate after B-track significance and documentation checks.")
    args = ap.parse_args()

    root = Path(__file__).resolve().parents[1]
    art = root / "docs" / "final" / "artifacts"
    gate_path = art / "sasang_4agent_promotion_gate_latest.json"
    gate_md_path = art / "sasang_4agent_promotion_gate_latest.md"
    approval_json_path = art / "sasang_4agent_human_approval_latest.json"
    approval_md_path = art / "sasang_4agent_human_approval_latest.md"

    gate = _safe_json(gate_path)
    if not gate:
        raise SystemExit(f"missing gate artifact: {gate_path}")

    ts = _now_utc()
    approval = {
        "schema": "sasang_4agent_human_approval_v1",
        "approved_at_utc": ts,
        "approver": args.approver,
        "approval_note": args.note,
        "input_gate_decision": gate.get("decision"),
        "approved": True,
    }
    approval_json_path.write_text(json.dumps(approval, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    approval_md_path.write_text(
        "\n".join(
            [
                "# Sasang 4-Agent Human Approval",
                "",
                f"- approved_at_utc: `{ts}`",
                f"- approver: `{args.approver}`",
                f"- approved: `True`",
                f"- input_gate_decision: `{gate.get('decision')}`",
                "",
                "## Note",
                args.note,
                "",
            ]
        ),
        encoding="utf-8",
    )

    gate["human_review_gate_required"] = False
    gate["auto_bridge_allowed"] = True
    gate["decision"] = "A_TRACK_PROMOTED_WITH_HUMAN_APPROVAL"
    gate["human_approval_ref"] = str(approval_json_path).replace("\\", "/")
    gate["approved_at_utc"] = ts
    gate["approved_by"] = args.approver
    gate["next_step"] = "Bridge is permitted by explicit human approval; execute controlled Track A rollout with monitoring."
    gate_path.write_text(json.dumps(gate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Sasang 4-Agent Promotion Gate",
        "",
        f"- generated_at_utc: `{gate.get('generated_at_utc')}`",
        f"- decision: `{gate.get('decision')}`",
        f"- human_review_gate_required: `{gate.get('human_review_gate_required')}`",
        f"- auto_bridge_allowed: `{gate.get('auto_bridge_allowed')}`",
        f"- approved_at_utc: `{gate.get('approved_at_utc')}`",
        f"- approved_by: `{gate.get('approved_by')}`",
        f"- human_approval_ref: `{gate.get('human_approval_ref')}`",
        "",
        "## Checks",
    ]
    checks = gate.get("checks") if isinstance(gate.get("checks"), dict) else {}
    for k, v in checks.items():
        lines.append(f"- {k}: `{v}`")
    lines.extend(["", "## Summary"])
    summary = gate.get("summary") if isinstance(gate.get("summary"), dict) else {}
    for k, v in summary.items():
        lines.append(f"- {k}: `{v}`")
    lines.extend(["", "## Next Step", f"- {gate.get('next_step')}", ""])
    gate_md_path.write_text("\n".join(lines), encoding="utf-8")

    print(str(approval_json_path))
    print(str(approval_md_path))
    print(str(gate_path))
    print(str(gate_md_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

