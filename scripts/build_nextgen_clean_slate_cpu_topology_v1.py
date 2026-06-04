#!/usr/bin/env python3
"""Materialize nextgen clean-slate CPU distributed topology spec (research_only)."""
from __future__ import annotations

import argparse
import json
import os
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXP = ROOT / "experiments/nextgen_clean_slate_cpu_v1"
DEFAULT_OUT = EXP / "topology_spec_v1_latest.json"
CHARTER = ROOT / "reports/btrack_nextgen_indexer_charter_v1_latest.json"
ACTIVE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p.resolve()).replace("\\", "/")


def _host_node(
    host_id: str,
    role: str,
    hostname: str | None = None,
    ip: str | None = None,
    shard_indices: list[int] | None = None,
) -> dict:
    return {
        "host_id": host_id,
        "hostname": hostname or platform.node(),
        "role": role,
        "ip": ip,
        "ram_gb": None,
        "cpu_logical": os.cpu_count(),
        "repo_root": str(ROOT).replace("\\", "/"),
        "shard_indices": shard_indices or ([0] if role == "primary" else [1]),
    }


def build_doc(
    aux_host: str | None,
    aux_ip: str | None,
    aux_share_root: str | None = None,
) -> dict:
    aux_list: list[dict] = []
    if aux_host or aux_ip or aux_share_root:
        node = _host_node(
            "aux0",
            "aux",
            hostname=aux_host or "DESKTOP-AP1DC83",
            ip=aux_ip,
            shard_indices=[1],
        )
        if aux_share_root:
            node["smb_share_root"] = aux_share_root.replace("\\", "/")
        aux_list.append(node)
    return {
        "schema": "nextgen_clean_slate_cpu_topology_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "track_a_active_write": False,
        "hypo_label": "[HYPO]",
        "charter_pointer": _rel(CHARTER) if CHARTER.is_file() else None,
        "hosts": {
            "primary": _host_node("main", "primary", shard_indices=[0]),
            "aux": aux_list,
        },
        "shard_policy": {
            "unit": "case_batch",
            "primary_shard_index": 0,
            "default_shard_count": 2 if aux_list else 1,
            "sync_model": "offline_batch",
            "note": "P1: fake weight blocks; P2: latent indexer stub (future)",
        },
        "latency_gates_ms": {
            "aux_shard_p95_max": 200,
            "loopback_p95_max": 50,
            "action_if_exceeded": "disable_aux_sharding; single-host CPU only",
        },
        "evaluation_ssot": {
            "baseline_json": _rel(
                EXP / "results/nextgen_neural_baseline_v1_latest.json"
            ),
            "golden40_compatible": False,
            "frozen_baseline_pointer": _rel(ACTIVE) if ACTIVE.is_file() else None,
        },
        "measurement_protocol": {
            "rtt_script": _rel(ROOT / "scripts/run_nextgen_clean_slate_cpu_rtt_probe_v1.py"),
            "payload_kb_grid": [64, 256, 1024],
            "rounds_default": 20,
        },
        "guardrails": [
            "No Track A active write",
            "No live trading trigger",
            "Golden-40 scores are parallel reference only",
            "FAIL-COMP-004: no auto-merge to MS or Track A headlines",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--aux-host", default=None, help="Aux PC hostname label")
    ap.add_argument("--aux-ip", default=None, help="Aux PC LAN IP for RTT probe")
    ap.add_argument(
        "--aux-share-root",
        default=None,
        help="Mapped SMB root e.g. Z:/",
    )
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    doc = build_doc(
        aux_host=args.aux_host,
        aux_ip=args.aux_ip,
        aux_share_root=args.aux_share_root,
    )
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "wrote": str(args.out_json),
                "shard_count": doc["shard_policy"]["default_shard_count"],
                "aux_configured": bool(doc["hosts"]["aux"]),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
