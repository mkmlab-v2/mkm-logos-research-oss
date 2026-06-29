#!/usr/bin/env python3
"""Portable launcher scripts for Edge Encoder SDK CLI [HYPO] B-track."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "reports/edge_encoder_sdk_portable_launcher_v1_latest"


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    root_ps = str(ROOT).replace("'", "''")

    smoke_ps1 = OUT_DIR / "edge-smoke.ps1"
    smoke_ps1.write_text(
        "\n".join(
            [
                "# Edge Encoder SDK smoke [HYPO] — requires Python + monorepo checkout",
                "$ErrorActionPreference = 'Stop'",
                f"$Root = '{root_ps}'",
                "Set-Location $Root",
                "py scripts/run_edge_encoder_sdk_cli_v1.py smoke",
                "",
            ]
        ),
        encoding="utf-8",
    )

    encode_ps1 = OUT_DIR / "edge-encode-manifest.ps1"
    encode_ps1.write_text(
        "\n".join(
            [
                "# Edge Encoder encode-manifest [HYPO]",
                "param([string]$EntryId = 'pilot_ninth_rib_55deg_v0')",
                "$ErrorActionPreference = 'Stop'",
                f"$Root = '{root_ps}'",
                "Set-Location $Root",
                "py scripts/run_edge_encoder_sdk_cli_v1.py encode-manifest --entry-id $EntryId",
                "",
            ]
        ),
        encoding="utf-8",
    )

    manifest = {
        "schema": "edge_encoder_sdk_portable_launcher_v1",
        "track": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "maturity": "launcher_scripts",
        "note": "Not a PyInstaller binary; portable PS1 wrappers for operator PoC.",
        "launchers": [
            "edge-smoke.ps1",
            "edge-encode-manifest.ps1",
        ],
        "requires": ["Python 3.11+", "monorepo checkout at build-time root"],
    }
    (OUT_DIR / "launcher_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"ok": True, "out": str(OUT_DIR)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
