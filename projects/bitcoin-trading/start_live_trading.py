#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PM2 / VPS 진입점 (모노레포 루트를 ``cwd``로 둘 때).

권장: ``cwd`` = 모노레포 루트, ``script`` = ``projects/bitcoin-trading/start_live_trading.py``
(``docs/final/LOCAL_VS_VPS_ONE_RULE_WORKFLOW.md`` 「VPS 배치 (권장)」).

실제 로직은 ``scripts/start_24h_daemon.py``에 두고, 여기서는 동일 프로세스 인자로 위임한다.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> None:
    bt_root = Path(__file__).resolve().parent
    daemon_script = bt_root / "scripts" / "start_24h_daemon.py"
    if not daemon_script.is_file():
        print(f"Missing daemon script: {daemon_script}", file=sys.stderr)
        raise SystemExit(2)
    raise SystemExit(
        subprocess.call([sys.executable, str(daemon_script)] + sys.argv[1:])
    )


if __name__ == "__main__":
    main()
