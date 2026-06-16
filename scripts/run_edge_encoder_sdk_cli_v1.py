#!/usr/bin/env python3
"""Edge Encoder SDK CLI v1 — local encode / validate / roundtrip [HYPO] B-track."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _workspace_root(args: argparse.Namespace) -> Path:
    return (args.workspace_root or ROOT).resolve()


def _cmd_encode_manifest(args: argparse.Namespace) -> int:
    ws = _workspace_root(args)
    sys.path.insert(0, str(ROOT))
    from scripts.edge_encoder_sdk_v1_lib import encode_from_manifest_entry

    result = encode_from_manifest_entry(
        args.entry_id,
        manifest_path=args.manifest,
        workspace_root=ws,
    )
    doc = result.to_dict()
    if args.out_json:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["ok"], "compact": result.compact, "tokens": result.token_proxy_cl100k}, ensure_ascii=False))
    return 0 if doc["ok"] else 1


def _cmd_validate(args: argparse.Namespace) -> int:
    ws = _workspace_root(args)
    sys.path.insert(0, str(ROOT))
    from scripts.edge_encoder_spec_v1_lib import (
        check_coord_wire_determinism,
        validate_coord_wire_minimal,
    )

    if args.wire_json:
        wire = json.loads(args.wire_json.read_text(encoding="utf-8"))
        if "coord_wire_minimal" in wire:
            wire = wire["coord_wire_minimal"]
    else:
        from scripts.edge_encoder_sdk_v1_lib import encode_from_manifest_entry

        wire = encode_from_manifest_entry(
            args.entry_id, manifest_path=args.manifest, workspace_root=ws
        ).wire

    errors = validate_coord_wire_minimal(wire) + check_coord_wire_determinism(wire, workspace_root=ws)
    print(json.dumps({"ok": not errors, "errors": errors}, ensure_ascii=False))
    return 0 if not errors else 1


def _cmd_local_roundtrip(args: argparse.Namespace) -> int:
    ws = _workspace_root(args)
    sys.path.insert(0, str(ROOT))
    from scripts.edge_encoder_sdk_v1_lib import encode_from_manifest_entry, local_roundtrip_v2_stub

    result = encode_from_manifest_entry(
        args.entry_id, manifest_path=args.manifest, workspace_root=ws
    )
    if result.validation_errors:
        print(json.dumps({"ok": False, "validation_errors": result.validation_errors}, ensure_ascii=False))
        return 1
    rt = local_roundtrip_v2_stub(result.wire, workspace_root=ws)
    if args.out_json:
        payload = {"encode": result.to_dict(), "roundtrip": rt}
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok": rt.get("ok"), "original_bulk_sent": False}, ensure_ascii=False))
    return 0 if rt.get("ok") else 1


def _cmd_smoke(args: argparse.Namespace) -> int:
    sys.path.insert(0, str(ROOT))
    from scripts.edge_encoder_sdk_v1_lib import encode_from_manifest_entry, local_roundtrip_v2_stub

    result = encode_from_manifest_entry("pilot_ninth_rib_55deg_v0", workspace_root=ROOT)
    if result.validation_errors:
        return 1
    rt = local_roundtrip_v2_stub(result.wire, workspace_root=ROOT)
    ok = result.token_proxy_cl100k is not None and rt.get("ok")
    print(json.dumps({"ok": ok, "tokens": result.token_proxy_cl100k}, ensure_ascii=False))
    return 0 if ok else 1


def _add_workspace_root(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--workspace-root",
        type=Path,
        default=None,
        help="Root for manifest local_path resolution (default: monorepo root).",
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)

    p_enc = sub.add_parser("encode-manifest", help="Build coord_wire from rib55 manifest entry (local base).")
    p_enc.add_argument("--entry-id", default="pilot_ninth_rib_55deg_v0")
    p_enc.add_argument("--manifest", type=Path, default=ROOT / "docs/final/artifacts/rib55_angle_overlay_manifest_v1.json")
    p_enc.add_argument("--out-json", type=Path, default=None)
    _add_workspace_root(p_enc)
    p_enc.set_defaults(func=_cmd_encode_manifest)

    p_val = sub.add_parser("validate", help="Schema + determinism validate wire JSON.")
    p_val.add_argument("--entry-id", default="pilot_ninth_rib_55deg_v0")
    p_val.add_argument("--wire-json", type=Path, default=None)
    p_val.add_argument("--manifest", type=Path, default=ROOT / "docs/final/artifacts/rib55_angle_overlay_manifest_v1.json")
    _add_workspace_root(p_val)
    p_val.set_defaults(func=_cmd_validate)

    p_rt = sub.add_parser("local-roundtrip", help="Encode locally + v2 stub roundtrip (no bulk upload).")
    p_rt.add_argument("--entry-id", default="pilot_ninth_rib_55deg_v0")
    p_rt.add_argument("--out-json", type=Path, default=None)
    p_rt.add_argument("--manifest", type=Path, default=ROOT / "docs/final/artifacts/rib55_angle_overlay_manifest_v1.json")
    _add_workspace_root(p_rt)
    p_rt.set_defaults(func=_cmd_local_roundtrip)

    p_smoke = sub.add_parser("smoke", help="Default entry encode + roundtrip smoke.")
    p_smoke.set_defaults(func=_cmd_smoke)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
