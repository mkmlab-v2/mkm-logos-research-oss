#!/usr/bin/env python3
"""PyInstaller-friendly entrypoint for Edge Encoder SDK [HYPO] B-track.

Frozen build supports encode-manifest + validate only (no in-process v2 stub).
Use HTTP roundtrip against customer-local v2 stub when deployed.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _resolve_roots() -> tuple[Path, Path]:
    if getattr(sys, "frozen", False):
        meipass = Path(getattr(sys, "_MEIPASS"))
        return meipass, meipass
    repo = Path(__file__).resolve().parents[1]
    return repo, repo


def main() -> int:
    repo_root, data_root = _resolve_roots()
    os.environ.setdefault("MKM_EDGE_ENCODER_DATA_ROOT", str(data_root))
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    import scripts.run_edge_encoder_sdk_cli_v1 as cli

    cli.ROOT = repo_root

    if getattr(sys, "frozen", False):
        if len(sys.argv) == 1 or (len(sys.argv) >= 2 and sys.argv[1] == "smoke"):
            from scripts.edge_encoder_sdk_v1_lib import frozen_smoke

            ok, summary = frozen_smoke(workspace_root=repo_root)
            print(__import__("json").dumps(summary, ensure_ascii=False))
            return 0 if ok else 1

    if not any(
        a in sys.argv
        for a in ("encode-manifest", "validate", "smoke", "local-roundtrip", "http-roundtrip")
    ):
        sys.argv = [sys.argv[0], "smoke", *sys.argv[1:]]
    return cli.main()


if __name__ == "__main__":
    raise SystemExit(main())
