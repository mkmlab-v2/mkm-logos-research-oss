#!/usr/bin/env python3
"""[HYPO] Edge Encoder SDK v1 — local base retention + coord_wire emit (B-track)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
WIRE_MODE = "anatomy_overlay_coord_v1"
DEFAULT_MANIFEST = ROOT / "docs/final/artifacts/rib55_angle_overlay_manifest_v1.json"
DEFAULT_BUNDLE_DIR = ROOT / "reports/edge_encoder_air_gap_bundle_v1_latest"
DEFAULT_PILOT_ENTRY_ID = "pilot_ninth_rib_55deg_v0"


def wire_compress_request_body(wire: dict[str, Any]) -> dict[str, Any]:
    wire_json = json.dumps(wire, ensure_ascii=False, separators=(",", ":"))
    entry_id = (wire.get("coord_inject") or {}).get("entry_id", "pilot")
    return {
        "text": wire_json,
        "loss_profile": "lossless_text",
        "sku_class": "coord",
        "stateless_packet": True,
        "client_request_id": f"edge-sdk-{entry_id}",
    }


def compression_packet_fingerprint(packet: dict[str, Any]) -> str:
    subset = {
        "compressed_text": packet.get("compressed_text"),
        "router_meta": packet.get("router_meta"),
        "loss_profile": packet.get("loss_profile"),
    }
    return json.dumps(subset, sort_keys=True, ensure_ascii=False)


@dataclass
class EdgeEncodeResult:
    wire: dict[str, Any]
    compact: str
    base_path_local: str
    base_sha256: str
    original_bulk_sent: bool = False
    validation_errors: list[str] = field(default_factory=list)
    token_proxy_cl100k: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "edge_encoder_sdk_encode_result_v1",
            "research_only": True,
            "send_gate": "HOLD",
            "original_bulk_sent": self.original_bulk_sent,
            "base_path_local": self.base_path_local,
            "base_sha256": self.base_sha256,
            "coord_wire_minimal": self.wire,
            "compact_coord_wire": self.compact,
            "token_proxy_cl100k": self.token_proxy_cl100k,
            "validation_errors": self.validation_errors,
            "ok": not self.validation_errors,
        }


def _token_proxy(text: str) -> int | None:
    try:
        import tiktoken

        return len(tiktoken.get_encoding("cl100k_base").encode(text))
    except Exception:
        return None


def frozen_smoke(*, workspace_root: Path = ROOT) -> tuple[bool, dict[str, Any]]:
    """Encode + validate only — no TestClient (frozen-friendly)."""
    from scripts.edge_encoder_spec_v1_lib import (
        check_coord_wire_determinism,
        validate_coord_wire_minimal,
    )

    result = encode_from_manifest_entry(DEFAULT_PILOT_ENTRY_ID, workspace_root=workspace_root)
    errors = list(result.validation_errors)
    if not errors:
        errors = validate_coord_wire_minimal(result.wire) + check_coord_wire_determinism(
            result.wire, workspace_root=workspace_root
        )
    summary = {
        "ok": not errors and result.token_proxy_cl100k is not None,
        "tokens": result.token_proxy_cl100k,
        "original_bulk_sent": False,
        "mode": "frozen_encode_validate",
        "errors": errors,
    }
    return summary["ok"], summary


def build_coord_wire(
    *,
    base_path: Path,
    entry_id: str,
    layer_id: str,
    points_norm: list[list[float]],
    coord_spec: str = WIRE_MODE,
    base_asset_title: str | None = None,
    stroke: str = "#E11D48",
    label_text: str = "coord overlay — [HYPO]",
    workspace_root: Path = ROOT,
) -> EdgeEncodeResult:
    from scripts.coord_anatomy_overlay_wire_v1_lib import compact_coord_wire
    from scripts.edge_encoder_spec_v1_lib import validate_coord_wire_minimal
    from scripts.rib55_angle_overlay_v1_lib import sha256_file

    base_path = base_path.resolve()
    if not base_path.is_file():
        raise FileNotFoundError(f"missing base image: {base_path}")

    base_sha = sha256_file(base_path)
    title = base_asset_title or base_path.name
    wire = {
        "sku_class": "coord",
        "wire_mode": WIRE_MODE,
        "base_asset_id": f"commons:{title}",
        "base_sha256": base_sha,
        "coord_inject": {
            "entry_id": entry_id,
            "layer_id": layer_id,
            "coord_spec": coord_spec,
            "points_norm": points_norm,
            "stroke": stroke,
            "label_text": label_text,
        },
    }
    compact = compact_coord_wire(wire)
    wire_json = json.dumps(wire, ensure_ascii=False, separators=(",", ":"))
    errors = validate_coord_wire_minimal(wire)
    return EdgeEncodeResult(
        wire=wire,
        compact=compact,
        base_path_local=str(base_path.relative_to(workspace_root)).replace("\\", "/"),
        base_sha256=base_sha,
        validation_errors=errors,
        token_proxy_cl100k=_token_proxy(wire_json),
    )


def encode_from_manifest_entry(
    entry_id: str,
    *,
    manifest_path: Path | None = None,
    workspace_root: Path = ROOT,
) -> EdgeEncodeResult:
    manifest_file = (manifest_path or DEFAULT_MANIFEST).resolve()
    doc = json.loads(manifest_file.read_text(encoding="utf-8"))
    entries = doc.get("entries") or []
    entry = next((e for e in entries if e.get("entry_id") == entry_id), None)
    if entry is None:
        raise KeyError(f"manifest entry not found: {entry_id}")

    base = entry.get("base_image") or {}
    local_rel = base.get("local_path")
    if not local_rel:
        raise ValueError(f"entry {entry_id} missing base_image.local_path")

    overlay = (entry.get("overlays") or [{}])[0]
    source = entry.get("source") or {}
    return build_coord_wire(
        base_path=workspace_root / local_rel,
        entry_id=entry_id,
        layer_id=str(overlay.get("layer_id") or "coord_layer"),
        points_norm=overlay.get("points_norm") or [],
        coord_spec=str(doc.get("coord_spec") or WIRE_MODE),
        base_asset_title=str(source.get("title") or Path(local_rel).name),
        stroke=str(overlay.get("stroke") or "#E11D48"),
        label_text=str(overlay.get("label_text") or "rib sweep — [HYPO]"),
        workspace_root=workspace_root,
    )


def local_roundtrip_v2_stub(
    wire: dict[str, Any],
    *,
    workspace_root: Path = ROOT,
) -> dict[str, Any]:
    """Local v2 stub compress→expand; no original bytes leave client process."""
    from fastapi.testclient import TestClient
    from scripts.compression_token_api_v2_stub import app
    from scripts.coord_anatomy_overlay_wire_v1_lib import materialize_coord_wire

    client = TestClient(app)
    cr = client.post("/v2/compress", json=wire_compress_request_body(wire))
    out: dict[str, Any] = {
        "compress_status": cr.status_code,
        "research_only": True,
        "original_bulk_sent": False,
    }
    if cr.status_code != 200:
        out["error"] = cr.text[:300]
        out["ok"] = False
        return out

    pkt = cr.json().get("compression_packet") or {}
    er = client.post(
        "/v2/expand",
        json={"compression_packet": pkt, "decode_mode": "codebook_only"},
    )
    out["expand_status"] = er.status_code
    if er.status_code != 200:
        out["error"] = er.text[:300]
        out["ok"] = False
        return out

    render = materialize_coord_wire(wire, workspace_root=workspace_root)
    out["local_render"] = {
        "output": render.get("output"),
        "base_sha256_match": render.get("base_sha256_match"),
    }
    out["expand_flags"] = er.json().get("integrity_flags")
    out["ok"] = bool(render.get("base_sha256_match"))
    return out


def build_air_gap_poc_pack(*, workspace_root: Path = ROOT) -> dict[str, Any]:
    from datetime import datetime, timezone

    bundle_rel = DEFAULT_BUNDLE_DIR.relative_to(workspace_root).as_posix()
    return {
        "schema": "edge_encoder_air_gap_poc_pack_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "track": "B",
        "research_only": True,
        "hypothesis_tier": "B",
        "send_gate": "HOLD",
        "deployment_mode": "air_gap_on_prem",
        "maturity": "bundle_materialized",
        "boundary_ack": (
            "[HYPO] LTM Graph OS + codebook package on customer VPC; "
            "MKM SaaS receives coord_wire only. Not production deploy."
        ),
        "stays_local": [
            "base_image_bytes",
            "full_overlay_render_png",
            "customer_private_corpus",
        ],
        "crosses_wire_only": [
            "coord_wire_minimal",
            "compact_coord_wire",
            "base_sha256 fingerprint",
            "metering_metadata",
        ],
        "sdk_cli": "scripts/run_edge_encoder_sdk_cli_v1.py",
        "spec": "docs/final/artifacts/edge_encoder_spec_v1_latest.json",
        "bundle_dir": bundle_rel,
        "bundle_builder": "scripts/build_edge_encoder_air_gap_bundle_v1.py",
        "bundle_gate": "scripts/check_edge_encoder_air_gap_bundle_v1.py",
        "invoke_chain": "scripts/Invoke-EdgeEncoderAirGapPoC_v1.ps1",
        "cross_process_http_gate": "scripts/check_edge_encoder_cross_process_determinism_v1.py",
        "portable_launcher": "scripts/build_edge_encoder_sdk_portable_launcher_v1.py",
        "reproduce": [
            "powershell -File scripts/Invoke-EdgeEncoderAirGapPoC_v1.ps1",
            "py scripts/build_edge_encoder_air_gap_poc_pack_v1.py",
            "py scripts/build_edge_encoder_air_gap_bundle_v1.py",
            "py scripts/check_edge_encoder_air_gap_bundle_v1.py",
            "py scripts/run_edge_encoder_sdk_cli_v1.py smoke",
        ],
    }


def _sha256_file(path: Path) -> str:
    from scripts.rib55_angle_overlay_v1_lib import sha256_file

    return sha256_file(path)


def _bundle_manifest_entry_slice(entry: dict[str, Any], *, local_path: str) -> dict[str, Any]:
    base = dict(entry.get("base_image") or {})
    base["local_path"] = local_path.replace("\\", "/")
    return {
        "coord_spec": "anatomy_overlay_coord_v1",
        "entries": [
            {
                "entry_id": entry.get("entry_id"),
                "base_image": base,
                "source": entry.get("source") or {},
                "overlays": entry.get("overlays") or [],
            }
        ],
    }


def materialize_air_gap_bundle(
    *,
    workspace_root: Path = ROOT,
    bundle_dir: Path | None = None,
    entry_id: str = DEFAULT_PILOT_ENTRY_ID,
) -> dict[str, Any]:
    """Copy local base + wire export into an offline bundle directory [HYPO]."""
    from datetime import datetime, timezone

    out_dir = (bundle_dir or DEFAULT_BUNDLE_DIR).resolve()
    manifest_src = (workspace_root / DEFAULT_MANIFEST.relative_to(ROOT)).resolve()
    doc = json.loads(manifest_src.read_text(encoding="utf-8"))
    entry = next((e for e in doc.get("entries") or [] if e.get("entry_id") == entry_id), None)
    if entry is None:
        raise KeyError(f"manifest entry not found: {entry_id}")

    base_src = workspace_root / str((entry.get("base_image") or {}).get("local_path"))
    if not base_src.is_file():
        raise FileNotFoundError(f"missing base image: {base_src}")

    rel_fixture = Path("data/anatomy/fixtures") / base_src.name
    bundle_fixture = out_dir / rel_fixture
    bundle_fixture.parent.mkdir(parents=True, exist_ok=True)
    bundle_fixture.write_bytes(base_src.read_bytes())

    manifest_rel = Path("docs/final/artifacts/rib55_bundle_manifest_entry_v1.json")
    manifest_out = out_dir / manifest_rel
    manifest_out.parent.mkdir(parents=True, exist_ok=True)
    slice_doc = _bundle_manifest_entry_slice(entry, local_path=rel_fixture.as_posix())
    manifest_out.write_text(json.dumps(slice_doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    encode = encode_from_manifest_entry(
        entry_id,
        manifest_path=manifest_out,
        workspace_root=out_dir,
    )
    wire_dir = out_dir / "wire"
    wire_dir.mkdir(parents=True, exist_ok=True)
    encode_path = wire_dir / "encode_result.json"
    encode_path.write_text(json.dumps(encode.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (wire_dir / "compact_coord_wire.txt").write_text(encode.compact + "\n", encoding="utf-8")
    wire_only = {
        "schema": "edge_encoder_wire_only_export_v1",
        "research_only": True,
        "send_gate": "HOLD",
        "original_bulk_sent": False,
        "base_sha256": encode.base_sha256,
        "base_asset_id": encode.wire.get("base_asset_id"),
        "coord_wire_minimal": encode.wire,
        "compact_coord_wire": encode.compact,
        "token_proxy_cl100k": encode.token_proxy_cl100k,
    }
    wire_only_path = wire_dir / "wire_only_export.json"
    wire_only_path.write_text(json.dumps(wire_only, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    operator = out_dir / "OPERATOR.txt"
    operator.write_text(
        "\n".join(
            [
                "Edge Encoder air-gap bundle [HYPO] — B-track PoC",
                "original_bulk_sent: false",
                "stays_local: base_image_bytes under data/anatomy/fixtures/",
                "crosses_wire_only: wire/wire_only_export.json",
                "",
                "Verify (from monorepo root):",
                "  py scripts/check_edge_encoder_air_gap_bundle_v1.py",
                "  powershell -File scripts/Invoke-EdgeEncoderAirGapPoC_v1.ps1",
                "",
            ]
        ),
        encoding="utf-8",
    )

    files: list[dict[str, Any]] = []
    for path in sorted(out_dir.rglob("*")):
        if not path.is_file() or path.name == "bundle_manifest.json":
            continue
        rel = path.relative_to(out_dir).as_posix()
        files.append({"path": rel, "sha256": _sha256_file(path), "bytes": path.stat().st_size})

    bundle_manifest = {
        "schema": "edge_encoder_air_gap_bundle_manifest_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "track": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "deployment_mode": "air_gap_on_prem",
        "entry_id": entry_id,
        "workspace_root": str(out_dir),
        "original_bulk_sent": False,
        "manifest": manifest_rel.as_posix(),
        "wire_only_export": "wire/wire_only_export.json",
        "file_count": len(files),
        "files": files,
    }
    manifest_path = out_dir / "bundle_manifest.json"
    manifest_path.write_text(json.dumps(bundle_manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    return {
        "ok": True,
        "bundle_dir": str(out_dir.relative_to(workspace_root)).replace("\\", "/"),
        "entry_id": entry_id,
        "file_count": len(files),
        "wire_only_export": wire_only_path.relative_to(workspace_root).as_posix(),
        "original_bulk_sent": False,
        "token_proxy_cl100k": encode.token_proxy_cl100k,
    }


def verify_air_gap_bundle(
    *,
    workspace_root: Path = ROOT,
    bundle_dir: Path | None = None,
    entry_id: str = DEFAULT_PILOT_ENTRY_ID,
) -> tuple[list[str], dict[str, Any]]:
    """Re-hash bundle files and re-encode from bundled manifest (no bulk upload)."""
    errors: list[str] = []
    out_dir = (bundle_dir or DEFAULT_BUNDLE_DIR).resolve()
    manifest_path = out_dir / "bundle_manifest.json"
    if not manifest_path.is_file():
        return [f"bundle: missing {manifest_path}"], {}

    recorded = json.loads(manifest_path.read_text(encoding="utf-8"))
    for row in recorded.get("files") or []:
        rel = str(row.get("path") or "")
        if not rel:
            continue
        if rel == "bundle_manifest.json":
            continue
        path = out_dir / rel
        if not path.is_file():
            errors.append(f"bundle: missing file {rel}")
            continue
        digest = _sha256_file(path)
        if digest != row.get("sha256"):
            errors.append(f"bundle: sha256 mismatch {rel}")

    manifest_entry = out_dir / str(recorded.get("manifest") or "")
    if not manifest_entry.is_file():
        errors.append(f"bundle: missing manifest entry {manifest_entry}")
    else:
        encode = encode_from_manifest_entry(
            entry_id,
            manifest_path=manifest_entry,
            workspace_root=out_dir,
        )
        if encode.validation_errors:
            errors.extend([f"bundle encode: {e}" for e in encode.validation_errors])
        wire_only_path = out_dir / str(recorded.get("wire_only_export") or "")
        if wire_only_path.is_file():
            wire_only = json.loads(wire_only_path.read_text(encoding="utf-8"))
            if wire_only.get("base_sha256") != encode.base_sha256:
                errors.append("bundle: wire_only_export base_sha256 drift")
            if wire_only.get("compact_coord_wire") != encode.compact:
                errors.append("bundle: compact_coord_wire drift")
        rt = local_roundtrip_v2_stub(encode.wire, workspace_root=out_dir)
        if not rt.get("ok"):
            errors.append("bundle: local_roundtrip failed")

    summary = {
        "bundle_dir": str(out_dir.relative_to(workspace_root)).replace("\\", "/"),
        "entry_id": entry_id,
        "file_count": recorded.get("file_count"),
        "original_bulk_sent": False,
        "roundtrip_ok": not errors,
    }
    return errors, summary
