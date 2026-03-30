from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Safe local guardian hook stub.")
    parser.add_argument("--file", dest="file_path", default="")
    args = parser.parse_args()

    payload = {
        "hook": "athena_local_guardian",
        "status": "ok",
        "file": args.file_path,
        "ts_utc": datetime.now(timezone.utc).isoformat(),
    }
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
