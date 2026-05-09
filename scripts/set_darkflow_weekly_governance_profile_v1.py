#!/usr/bin/env python3
"""Set active darkflow weekly governance policy from preset."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
ACTIVE = ART / "darkflow_weekly_governance_policy_v1.json"
PRESETS = {
    "conservative": ART / "darkflow_weekly_governance_policy_preset_conservative_v1.json",
    "aggressive": ART / "darkflow_weekly_governance_policy_preset_aggressive_v1.json",
}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Set active darkflow weekly governance profile.")
    ap.add_argument("--profile", choices=["conservative", "aggressive"], required=True)
    args = ap.parse_args()

    src = PRESETS[args.profile]
    if not src.exists():
        raise FileNotFoundError(f"Missing preset file: {src}")

    policy = _load(src)
    policy["profile"] = args.profile
    policy["activated_at_utc"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    ACTIVE.write_text(json.dumps(policy, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(ACTIVE))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
