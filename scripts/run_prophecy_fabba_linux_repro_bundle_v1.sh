#!/usr/bin/env bash
# [HYPO] Linux/WSL fABBA wheel A/B repro bundle (B-track, research_only).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
VENV="$ROOT/.venv-fabba-linux-repro"
PY="$VENV/bin/python"

echo "==> host: $(uname -a)"
if [[ ! -x "$PY" ]]; then
  python3 -m venv "$VENV"
fi
echo "==> python: $($PY --version 2>&1)"

"$VENV/bin/pip" install --upgrade pip setuptools wheel >/dev/null
"$VENV/bin/pip" install fABBA numpy scipy pandas scikit-learn matplotlib >/dev/null

"$PY" - <<'PY'
import importlib.util
spec = importlib.util.find_spec("fABBA")
print("fABBA_spec", spec)
if not spec:
    raise SystemExit("fABBA not importable after pip install")
PY

OUT="$ROOT/reports/prophecy_fabba_backend_ab_linux_wsl_v1_latest.json"
"$PY" "$ROOT/scripts/run_prophecy_fabba_backend_ab_dual_leg_v1.py" --output "$OUT"

"$PY" "$ROOT/scripts/run_prophecy_edge_shadow_chain_closure_v1.py"

echo "WROTE: $OUT"
"$PY" - <<PY
import json
from pathlib import Path
p = Path("$OUT")
doc = json.loads(p.read_text(encoding="utf-8"))
print("fabba_native", doc.get("fabba_native_available"))
print("delta", (doc.get("compare") or {}).get("ngram_hr_delta_fabba_minus_apca"))
PY
