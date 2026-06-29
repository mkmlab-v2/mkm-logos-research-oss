#!/usr/bin/env python3
"""Build PyInstaller spec + readiness manifest for Edge Encoder SDK [HYPO]."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "reports/edge_encoder_sdk_pyinstaller_v1_latest"
ENTRY = ROOT / "scripts/edge_encoder_sdk_frozen_entrypoint_v1.py"
READINESS = ROOT / "reports/edge_encoder_pyinstaller_readiness_v1_latest.json"
ARTIFACT = ROOT / "docs/final/artifacts/edge_encoder_pyinstaller_readiness_v1_latest.json"

DATAS = [
    "docs/final/artifacts/rib55_angle_overlay_manifest_v1.json",
    "docs/final/schemas/edge_encoder_coord_wire_v1.schema.json",
    "docs/final/schemas/edge_encoder_spec_v1.schema.json",
    "data/anatomy/fixtures/ninth_rib_lateral2.png",
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _pyinstaller_available() -> bool:
    return importlib.util.find_spec("PyInstaller") is not None


def _extra_datas() -> list[tuple[str, str]]:
    rows = list(DATAS)
    try:
        import rfc3987_syntax

        grammar = Path(rfc3987_syntax.__file__).resolve().parent / "syntax_rfc3987.lark"
        if grammar.is_file():
            rows.append(str(grammar.relative_to(ROOT)) if grammar.is_relative_to(ROOT) else str(grammar))
    except Exception:
        pass
    return rows


def _spec_text() -> str:
    data_lines = []
    for rel in _extra_datas():
        src = Path(rel) if Path(rel).is_absolute() else ROOT / rel
        if src.is_file():
            if src.is_relative_to(ROOT):
                dest_dir = str(src.relative_to(ROOT).parent).replace("\\", "/")
            else:
                dest_dir = "rfc3987_syntax"
            data_lines.append(f"        (r'{src}', r'{dest_dir}'),")
    datas_block = "\n".join(data_lines) if data_lines else "        # no datas resolved"

    return f"""# -*- mode: python ; coding: utf-8 -*-
# [HYPO] Edge Encoder SDK frozen entrypoint — B-track scaffold

block_cipher = None

a = Analysis(
    [r'{ENTRY}'],
    pathex=[r'{ROOT}'],
    binaries=[],
    datas=[
{datas_block}
    ],
    hiddenimports=[
        'scripts.edge_encoder_sdk_v1_lib',
        'scripts.edge_encoder_spec_v1_lib',
        'scripts.coord_anatomy_overlay_wire_v1_lib',
        'scripts.rib55_angle_overlay_v1_lib',
        'jsonschema',
        'tiktoken',
        'tiktoken_ext.openai_public',
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='mkm-edge-encoder-sdk',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
"""


def build_readiness(*, built: bool, exe_path: Path | None, error: str | None = None) -> dict:
    if built:
        status = "binary_built"
    elif not _pyinstaller_available():
        status = "spec_ready_pyinstaller_missing"
    else:
        status = "spec_ready"
    return {
        "schema": "edge_encoder_pyinstaller_readiness_v1",
        "generated_at_utc": _utc(),
        "track": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "status": status,
        "pyinstaller_installed": _pyinstaller_available(),
        "entrypoint": "scripts/edge_encoder_sdk_frozen_entrypoint_v1.py",
        "spec_path": str((OUT_DIR / "edge_encoder_sdk_cli_v1.spec").relative_to(ROOT)).replace("\\", "/"),
        "out_dir": str(OUT_DIR.relative_to(ROOT)).replace("\\", "/"),
        "exe_path": str(exe_path.relative_to(ROOT)).replace("\\", "/") if exe_path and exe_path.is_file() else None,
        "supported_commands_frozen": ["encode-manifest", "validate", "smoke"],
        "unsupported_frozen_note": "local-roundtrip/http-roundtrip require v2 stub HTTP; not embedded in onefile.",
        "build_error": error,
        "reproduce": [
            "py scripts/build_edge_encoder_sdk_pyinstaller_v1.py",
            "py scripts/build_edge_encoder_sdk_pyinstaller_v1.py --build",
            "py scripts/check_edge_encoder_pyinstaller_readiness_v1.py",
        ],
    }


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--build", action="store_true", help="Run PyInstaller when installed.")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    spec_path = OUT_DIR / "edge_encoder_sdk_cli_v1.spec"
    spec_path.write_text(_spec_text(), encoding="utf-8")

    exe_path: Path | None = None
    build_error: str | None = None
    if args.build:
        if not _pyinstaller_available():
            build_error = "PyInstaller not installed; spec only"
        else:
            proc = subprocess.run(
                [sys.executable, "-m", "PyInstaller", "--noconfirm", "--distpath", str(OUT_DIR / "dist"), str(spec_path)],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
            )
            if proc.returncode != 0:
                build_error = (proc.stderr or proc.stdout or "PyInstaller failed")[:500]
            else:
                candidate = OUT_DIR / "dist" / "mkm-edge-encoder-sdk.exe"
                if candidate.is_file():
                    exe_path = candidate
    elif (OUT_DIR / "dist" / "mkm-edge-encoder-sdk.exe").is_file():
        exe_path = OUT_DIR / "dist" / "mkm-edge-encoder-sdk.exe"

    doc = build_readiness(built=exe_path is not None, exe_path=exe_path, error=build_error)
    payload = json.dumps(doc, indent=2, ensure_ascii=False) + "\n"
    READINESS.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    READINESS.write_text(payload, encoding="utf-8")
    ARTIFACT.write_text(payload, encoding="utf-8")
    print(json.dumps({"ok": build_error is None or not args.build, "status": doc["status"], "exe": doc.get("exe_path")}, ensure_ascii=False))
    return 0 if build_error is None or not args.build else 1


if __name__ == "__main__":
    raise SystemExit(main())
