#!/usr/bin/env python3
"""Launch chat shim with workspace .env upstream applied (B-track dogfood)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.sandbox.check_chat_shim_upstream_env_v1 import apply_upstream_env  # noqa: E402


def main() -> None:
    apply_upstream_env()
    os.environ.setdefault(
        "COMPRESSION_HARDENING_CONFIG_PATH",
        str(ROOT / "data/btrack/compression_coding_proxy_hardening_v1.json"),
    )
    os.environ.pop("MKM_CHAT_SHIM_DRY_RUN", None)
    port = int(os.environ.get("MKM_CHAT_SHIM_PORT", "8011"))
    import uvicorn

    uvicorn.run(
        "scripts.cursor_chat_shim_v1:app",
        host="127.0.0.1",
        port=port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
