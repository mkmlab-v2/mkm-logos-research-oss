from __future__ import annotations

import json
from datetime import datetime, timezone


def main() -> int:
    payload = {
        "hook": "auto_consolidate_rules",
        "status": "ok",
        "mode": "stub",
        "ts_utc": datetime.now(timezone.utc).isoformat(),
    }
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
