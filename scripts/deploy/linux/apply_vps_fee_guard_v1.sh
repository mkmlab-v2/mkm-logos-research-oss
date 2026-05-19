#!/usr/bin/env bash
# Apply max_trades_per_day cap on VPS risk profile (no prophecy routing).
set -euo pipefail
REPO="${1:-/opt/mkm-destiny-ai-41e38ec6}"
MAX="${MKM_FEE_GUARD_MAX_TRADES_PER_DAY:-6}"
RISK="$REPO/projects/bitcoin-trading/memory/v2/risk/risk_profile_fact_safe_latest.json"
if [[ ! -f "$RISK" ]]; then
  echo "MISSING: $RISK" >&2
  exit 2
fi
python3 - "$RISK" "$MAX" <<'PY'
import json
import sys
from pathlib import Path

p = Path(sys.argv[1])
cap = int(sys.argv[2])
d = json.loads(p.read_text(encoding="utf-8"))
before = d.get("max_trades_per_day")
d["max_trades_per_day"] = min(int(d.get("max_trades_per_day") or 99), cap)
d["maker_only_level"] = "strict"
note = "fee_guard_vps_commander_approved_v1"
prior = str(d.get("notes") or "")
if note not in prior:
    d["notes"] = f"{prior} | {note}".strip(" |")
p.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"max_trades_per_day: {before} -> {d['max_trades_per_day']}")
PY
echo "[OK] fee guard applied on $RISK"
