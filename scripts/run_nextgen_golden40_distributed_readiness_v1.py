#!/usr/bin/env python3
"""[HYPO] Aux/share readiness for Golden-40 distributed + P1 (ports, artifacts)."""
from __future__ import annotations

import argparse
import json
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_golden40_distributed_readiness_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _tcp_open(host: str, port: int, timeout: float = 3.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--aux-ip", default="180.224.2.24")
    ap.add_argument("--share-root", type=Path, default=Path("Z:/nextgen_cpu_aux"))
    args = ap.parse_args()

    share = args.share_root
    shard1_aux = share / "ng40_golden40_shard1_v1_latest.json"
    publish_stamp = share / "ng40_shard1_publish_from_main_v1.json"
    aux_drop_files = [
        "RUN_RTT_SERVER_ON_AUX.cmd",
        "RUN_P1_SERVER_ON_AUX.cmd",
        "RUN_NG40_SHARD_ON_AUX.cmd",
    ]
    present = {f: (share / f).is_file() for f in aux_drop_files}

    doc = {
        "schema": "ng40_golden40_distributed_readiness_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "aux_ip": args.aux_ip,
        "share_root": str(share),
        "share_mounted": share.parent.exists(),
        "ports": {
            "rtt_19876": _tcp_open(args.aux_ip, 19876),
            "p1_19877": _tcp_open(args.aux_ip, 19877),
        },
        "shard1_on_share": shard1_aux.is_file(),
        "shard1_aux_path": str(shard1_aux),
        "shard1_publish_stamp_on_share": publish_stamp.is_file(),
        "shard1_likely_publish_copy_not_aux_run": publish_stamp.is_file(),
        "aux_drop_cmds_present": present,
        "ready_for_share_merge_path": shard1_aux.is_file(),
        "ready_for_true_aux_merge": shard1_aux.is_file() and not publish_stamp.is_file(),
        "ready_for_p1_probe": _tcp_open(args.aux_ip, 19877),
        "operator_next": [],
    }
    if not doc["ports"]["p1_19877"]:
        doc["operator_next"].append(
            "Aux: Z:\\nextgen_cpu_aux\\RUN_P1_SERVER_ON_AUX.cmd (and RTT if needed)"
        )
    if doc.get("shard1_likely_publish_copy_not_aux_run"):
        doc["operator_next"].append(
            "Z:\\ shard1 is publish-from-main copy; delete ng40_shard1_publish_from_main_v1.json "
            "and re-run RUN_NG40_SHARD_ON_AUX.cmd on aux for true aux compute"
        )
    if not doc["shard1_on_share"]:
        doc["operator_next"].append(
            "Aux: Z:\\nextgen_cpu_aux\\RUN_NG40_SHARD_ON_AUX.cmd then re-run distributed chain"
        )
    if not doc["share_mounted"]:
        doc["operator_next"].append("Mount SMB Z:\\ to DESKTOP-AP1DC83\\share")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(OUT), **{k: doc[k] for k in (
        "ports", "shard1_on_share", "ready_for_true_aux_merge", "ready_for_p1_probe"
    )}}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
