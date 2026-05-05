from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build human-readable MKM AI status brief.")
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

    pointer_path = root / "docs" / "final" / "artifacts" / "mkm_ai_status_pointer_latest.json"
    weekly_path = root / "docs" / "final" / "artifacts" / "mkm_ai_v2_weekly_readiness_report_latest.json"
    decision_path = root / "docs" / "final" / "artifacts" / "mkm_ai_v2_promotion_decision_latest.json"
    out_path = root / "docs" / "final" / "artifacts" / "mkm_ai_status_brief_latest.md"

    pointer = _read_json(pointer_path)
    weekly = _read_json(weekly_path)
    decision = _read_json(decision_path)

    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    status = pointer.get("status", "UNKNOWN")
    label = pointer.get("system_label", "Unknown")
    is_final = bool(pointer.get("is_final", False))
    pass_rate = weekly.get("pass_rate_percent")
    sample_count = weekly.get("sample_count")
    promo_decision = decision.get("decision")
    reasons = decision.get("reasons", [])
    reason_text = "; ".join(str(r) for r in reasons) if reasons else "n/a"

    lines = [
        "# MKM AI Status Brief (Latest)",
        "",
        f"- generated_at_utc: `{now}`",
        f"- status: `{status}`",
        f"- system_label: `{label}`",
        f"- is_final: `{str(is_final).lower()}`",
        f"- promotion_decision: `{promo_decision}`",
        f"- weekly_pass_rate_percent: `{pass_rate}`",
        f"- weekly_sample_count: `{sample_count}`",
        f"- decision_reasons: `{reason_text}`",
        "",
        "## Evidence",
        f"- `docs/final/artifacts/{pointer_path.name}`",
        f"- `docs/final/artifacts/{weekly_path.name}`",
        f"- `docs/final/artifacts/{decision_path.name}`",
    ]

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"status brief written: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
