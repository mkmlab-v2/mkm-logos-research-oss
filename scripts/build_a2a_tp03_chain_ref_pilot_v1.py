#!/usr/bin/env python3
"""tp03 pilot — Track C fusion artifacts → pointer + fingerprint handoff rows.

[HYPO] / research_only. Disk JSON stays SSOT; agent context gets compact refs only.

  py scripts/build_a2a_tp03_chain_ref_pilot_v1.py
  py scripts/build_a2a_tp03_chain_ref_pilot_v1.py --strict-exit
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from mkm_a2a_compress_pilot_lib_v1 import (  # noqa: E402
    compress_plaintext_v2,
    count_tokens,
    load_compress_skip_rules,
)

DEFAULT_OUT = ROOT / "docs/final/artifacts/a2a_tp03_chain_ref_pilot_v1_latest.json"

# Track C / multilens chain artifacts — pointer targets (human publish bodies excluded).
TRACKC_REF_TARGETS: list[dict[str, str]] = [
    {
        "id": "trackc_ops_dashboard",
        "path": "docs/final/artifacts/mkm_trackc_ops_dashboard_latest.json",
        "chain_step": "Invoke-TrackCMacroDailyFusion_v1.ps1 (terminal dashboard)",
    },
    {
        "id": "logos_insight_bundle",
        "path": "docs/final/artifacts/logos_insight_bundle_v1_latest.json",
        "chain_step": "build_logos_insight_bundle_v1.py",
    },
    {
        "id": "cross_lens_rag_fusion",
        "path": "docs/final/artifacts/cross_lens_rag_fusion_report_v1_latest.json",
        "chain_step": "build_cross_lens_rag_fusion_v1.py",
    },
    {
        "id": "showroom_macro_horizon_2030_slice",
        "path": "docs/final/artifacts/showroom_macro_horizon_2030_slice_v1_latest.json",
        "chain_step": "build_showroom_macro_horizon_2030_slice_v1.py",
        "note": "disk SSOT for showroom; public HTML fetch unchanged — agent pointer only",
    },
    {
        "id": "logos_macro_horizon_2030",
        "path": "docs/final/artifacts/logos_macro_horizon_2030_scenario_v1_latest.json",
        "chain_step": "build_logos_macro_horizon_2030_scenario_v1.py",
    },
    {
        "id": "inter_agent_trackc_rq019_slice",
        "path": "docs/final/artifacts/mkm_inter_agent_trackc_rq019_slice_v1_latest.json",
        "chain_step": "build_mkm_inter_agent_trackc_rq019_slice_v1.py",
    },
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _essence_line(doc: dict[str, Any], *, artifact_id: str) -> str:
    schema = doc.get("schema") or artifact_id
    parts = [f"schema={schema}"]
    for key in ("generated_at_utc", "status", "final_action", "research_only"):
        if key in doc and doc[key] is not None:
            parts.append(f"{key}={doc[key]}")
    system = doc.get("system")
    if isinstance(system, dict):
        for key in ("status", "promotion_decision"):
            if system.get(key) is not None:
                parts.append(f"system.{key}={system[key]}")
    trackc = doc.get("trackc")
    if isinstance(trackc, dict) and trackc.get("packet_status") is not None:
        parts.append(f"trackc.packet_status={trackc['packet_status']}")
    return " ".join(parts)


def _pointer_row(
    *,
    artifact_id: str,
    rel_path: str,
    chain_step: str,
    sha256: str,
    doc: dict[str, Any] | None,
    note: str | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "artifact_id": artifact_id,
        "artifact_path": rel_path.replace("\\", "/"),
        "sha256": sha256,
        "chain_step": chain_step,
        "handoff_mode": "pointer_plus_fingerprint",
    }
    if note:
        row["note"] = note
    if isinstance(doc, dict):
        if doc.get("schema"):
            row["schema"] = doc["schema"]
        if doc.get("generated_at_utc"):
            row["generated_at_utc"] = doc["generated_at_utc"]
        row["essence_line"] = _essence_line(doc, artifact_id=artifact_id)
    else:
        row["essence_line"] = f"schema=unknown artifact_id={artifact_id}"
    return row


def _analyze_artifact(root: Path, spec: dict[str, str], *, min_tokens: int, client: Any) -> dict[str, Any]:
    rel = spec["path"]
    path = root / rel
    row: dict[str, Any] = {
        "artifact_id": spec["id"],
        "artifact_path": rel.replace("\\", "/"),
        "chain_step": spec["chain_step"],
        "exists": path.is_file(),
    }
    if spec.get("note"):
        row["note"] = spec["note"]
    if not path.is_file():
        row["missing"] = True
        return row

    raw = path.read_text(encoding="utf-8-sig")
    sha = _sha256_file(path)
    doc: dict[str, Any] | None = None
    try:
        doc = json.loads(raw)
    except json.JSONDecodeError:
        doc = None

    full_tokens = count_tokens(raw)
    pointer = _pointer_row(
        artifact_id=spec["id"],
        rel_path=rel,
        chain_step=spec["chain_step"],
        sha256=sha,
        doc=doc,
        note=spec.get("note"),
    )
    pointer_text = json.dumps(pointer, ensure_ascii=False, separators=(",", ":"))
    pointer_tokens = count_tokens(pointer_text)
    full_t = int(full_tokens["tokens"])
    ptr_t = int(pointer_tokens["tokens"])
    saved = max(0, full_t - ptr_t)
    ratio = round(saved / full_t, 6) if full_t else 0.0

    essence = pointer.get("essence_line") or ""
    compress_row = compress_plaintext_v2(
        client,
        essence,
        min_tokens=min_tokens,
        routing_profile="track_a_promoted",
        client_request_id=f"a2a-tp03-{spec['id']}",
    )

    row.update(
        {
            "sha256": sha,
            "char_count": len(raw),
            "full_body_tokens": full_t,
            "pointer_tokens": ptr_t,
            "tokens_saved_pointer_vs_full": saved,
            "reduction_ratio_pointer_vs_full": ratio,
            "token_count_method": full_tokens.get("method"),
            "pointer_handoff": pointer,
            "essence_compress": compress_row,
        }
    )
    return row


def build_pilot_document(root: Path) -> dict[str, Any]:
    skip_rules = load_compress_skip_rules(root)
    min_tokens = int(skip_rules.get("min_plaintext_tokens_recommend") or 32)

    from fastapi.testclient import TestClient

    from scripts.compression_token_api_v2_stub import app

    client = TestClient(app)
    artifacts: list[dict[str, Any]] = []
    present: list[dict[str, Any]] = []
    for spec in TRACKC_REF_TARGETS:
        analyzed = _analyze_artifact(root, spec, min_tokens=min_tokens, client=client)
        artifacts.append(analyzed)
        if analyzed.get("exists"):
            present.append(analyzed)

    total_full = sum(int(a.get("full_body_tokens") or 0) for a in present)
    total_ptr = sum(int(a.get("pointer_tokens") or 0) for a in present)
    total_saved = max(0, total_full - total_ptr)
    aggregate_ratio = round(total_saved / total_full, 6) if total_full else None

    return {
        "schema": "a2a_tp03_chain_ref_pilot_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tier": "B",
        "target_point_id": "tp03_trackc_multilens_chain_refs",
        "status": "PILOT",
        "boundary_ack": (
            "[HYPO] tp03 pointer+fingerprint pilot. Disk JSON/HTML publish unchanged. "
            "Agent handoff uses compact refs only. No Track A·live merge."
        ),
        "a2a_target_points_ssot": "docs/final/artifacts/a2a_target_points_v1_latest.json",
        "compress_skip_rules_applied": skip_rules,
        "chain_wrappers": [
            "scripts/Invoke-TrackCMacroDailyFusion_v1.ps1",
            "scripts/Invoke-PremiumMultilensQueueRoutine_v1.ps1",
        ],
        "artifacts_present": len(present),
        "artifacts_missing": sum(1 for a in artifacts if not a.get("exists")),
        "aggregate_pointer_vs_full": {
            "full_body_tokens_sum": total_full,
            "pointer_tokens_sum": total_ptr,
            "tokens_saved_sum": total_saved,
            "reduction_ratio": aggregate_ratio,
            "reduction_percent": round((aggregate_ratio or 0) * 100, 2),
        },
        "artifacts": artifacts,
        "kpi_headline": {
            "reduction_percent_if_pointers_only": round((aggregate_ratio or 0) * 100, 2),
            "largest_artifact_id": max(present, key=lambda x: x.get("full_body_tokens") or 0)["artifact_id"]
            if present
            else None,
        },
        "evidence_paths": [
            "scripts/build_a2a_tp03_chain_ref_pilot_v1.py",
            "scripts/mkm_a2a_compress_pilot_lib_v1.py",
            "scripts/Invoke-TrackCMacroDailyFusion_v1.ps1",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--strict-exit",
        action="store_true",
        help="Exit 1 if zero Track C artifacts found on disk",
    )
    args = ap.parse_args()

    doc = build_pilot_document(ROOT)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    agg = doc.get("aggregate_pointer_vs_full") or {}
    print(f"WROTE: {args.out}")
    print(
        f"present={doc.get('artifacts_present')} "
        f"saved_tokens={agg.get('tokens_saved_sum')} "
        f"reduction={agg.get('reduction_percent')}%"
    )
    if args.strict_exit and int(doc.get("artifacts_present") or 0) == 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
