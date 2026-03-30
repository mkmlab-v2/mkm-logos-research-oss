from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DECISION = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_DECISION_V1.json"


def main() -> int:
    status = "ok"
    mode = "stub"
    go_no_go = "UNKNOWN"
    if DECISION.is_file():
        doc = json.loads(DECISION.read_text(encoding="utf-8"))
        go_no_go = str(doc.get("go_no_go", "UNKNOWN"))
        status = "ok" if go_no_go == "GO" else "rollback_required"
        mode = str(doc.get("rollout_policy", "stub"))
    payload = {
        "hook": "token_circuit_breaker",
        "status": status,
        "mode": mode,
        "go_no_go": go_no_go,
        "decision_artifact": str(DECISION.relative_to(ROOT)).replace("\\", "/"),
        "ts_utc": datetime.now(timezone.utc).isoformat(),
    }
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
