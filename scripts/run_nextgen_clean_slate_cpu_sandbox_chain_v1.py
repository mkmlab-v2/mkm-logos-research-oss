#!/usr/bin/env python3
"""Next-Gen clean-slate CPU sandbox chain: topology → RTT → P0 → P1 → NG baseline."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
EXP = ROOT / "experiments/nextgen_clean_slate_cpu_v1"
TOPOLOGY = EXP / "topology_spec_v1_latest.json"
RTT_OUT = EXP / "results/rtt_probe_v1_latest.json"
P0_OUT = EXP / "results/p0_microbench_v1_latest.json"
P1_OUT = EXP / "results/p1_shard_ping_v1_latest.json"
BASELINE_OUT = EXP / "results/nextgen_neural_baseline_v1_latest.json"
NG40_SHADOW_OUT = EXP / "results/ng40_latent_stub_shadow_v1_latest.json"
NG40_POC_OUT = EXP / "results/ng40_latent_poc_v1_latest.json"
ACTIVE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p.resolve()).replace("\\", "/")


def _run(
    script: str,
    extra: list[str] | None = None,
    timeout_s: int | None = 600,
) -> dict[str, Any]:
    cmd = [sys.executable, str(ROOT / script)] + (extra or [])
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        timed_out = False
    except subprocess.TimeoutExpired:
        proc = None
        timed_out = True
    return {
        "command": " ".join(cmd),
        "exit_code": 124 if timed_out else (proc.returncode if proc else -1),
        "timed_out": timed_out,
        "timeout_s": timeout_s,
        "stdout_tail": ((proc.stdout or "") if proc else "")[-600:],
        "stderr_tail": ((proc.stderr or "") if proc else "subprocess timeout")[-300:],
    }


def _load_json(path: Path) -> dict | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _frozen_snapshot() -> dict:
    doc = _load_json(ACTIVE)
    if not doc:
        return {"present": False}
    cm = doc.get("compression_metrics") or {}
    return {
        "present": True,
        "global_token_saving_rate": cm.get("global_token_saving_rate"),
        "avg_reconstruction_fidelity_jaccard": cm.get(
            "avg_reconstruction_fidelity_jaccard"
        ),
        "alignment_pass_rate_raw": cm.get("alignment_pass_rate_raw"),
        "note": "parallel reference only; NG baseline is not Golden-40 compatible",
    }


def _latency_verdict(topology: dict | None, rtt: dict | None) -> dict:
    gates = (topology or {}).get("latency_gates_ms") or {}
    loop_max = float(gates.get("loopback_p95_max") or 50)
    aux_max = float(gates.get("aux_shard_p95_max") or 200)

    loop_p95 = None
    if rtt and rtt.get("mode") == "loopback":
        grid = (rtt.get("measurement") or {}).get("grid") or []
        p95_vals = [
            g.get("rtt_ms", {}).get("p95")
            for g in grid
            if g.get("rtt_ms", {}).get("p95") is not None
        ]
        if p95_vals:
            loop_p95 = max(p95_vals)
    elif rtt and rtt.get("mode") == "client":
        loop_p95 = (rtt.get("measurement") or {}).get("rtt_ms", {}).get("p95")

    aux_ok = None
    if rtt and rtt.get("mode") == "client":
        aux_ok = loop_p95 is not None and loop_p95 <= aux_max

    loop_ok = loop_p95 is not None and loop_p95 <= loop_max if loop_p95 else None

    return {
        "loopback_p95_ms": loop_p95,
        "loopback_gate_ms": loop_max,
        "loopback_pass": loop_ok,
        "aux_p95_ms": loop_p95 if rtt and rtt.get("mode") == "client" else None,
        "aux_gate_ms": aux_max,
        "aux_pass": aux_ok,
        "recommendation": (
            "disable_aux_sharding; single-host CPU only"
            if aux_ok is False
            else "proceed_poc_v0"
        ),
    }


def _merged_latency(
    topology: dict | None, rtt_loop: dict | None, rtt_aux: dict | None
) -> dict:
    loop_v = _latency_verdict(topology, rtt_loop)
    if not rtt_aux or rtt_aux.get("mode") != "client":
        return loop_v
    aux_max = float((topology or {}).get("latency_gates_ms", {}).get("aux_shard_p95_max") or 200)
    aux_p95 = (rtt_aux.get("measurement") or {}).get("rtt_ms", {}).get("p95")
    aux_ok = aux_p95 is not None and aux_p95 <= aux_max
    loop_v["aux_p95_ms"] = aux_p95
    loop_v["aux_gate_ms"] = aux_max
    loop_v["aux_pass"] = aux_ok
    if aux_ok is False:
        loop_v["recommendation"] = "disable_aux_sharding; single-host CPU only"
    return loop_v


def build_plan(
    execute: bool,
    aux_host: str | None,
    aux_ip: str | None,
    aux_share_root: str | None = None,
    skip_aux_deploy: bool = False,
    main_only: bool = False,
) -> dict:
    if main_only:
        aux_host = None
        aux_ip = None
        aux_share_root = None
        skip_aux_deploy = True
    steps: list[dict] = []
    topo_args = ["--out-json", str(TOPOLOGY)]
    if aux_host:
        topo_args.extend(["--aux-host", aux_host])
    if aux_ip:
        topo_args.extend(["--aux-ip", aux_ip])
    if aux_share_root:
        topo_args.extend(["--aux-share-root", aux_share_root])

    if aux_share_root:
        step_defs_share = []
        if not skip_aux_deploy:
            step_defs_share.append(
                (
                    "T0b_deploy_aux_drop",
                    "scripts/deploy_nextgen_clean_slate_cpu_aux_drop_v1.py",
                    [
                        "--share-root",
                        str(Path(aux_share_root.rstrip("/\\")) / "nextgen_cpu_aux"),
                        "--merge-only",
                    ],
                    False,
                    120,
                )
            )
        step_defs_share.append(
            (
                "T0c_share_bus_probe",
                "scripts/run_nextgen_clean_slate_cpu_share_bus_probe_v1.py",
                ["--share-root", aux_share_root],
                False,
                180,
            )
        )
    else:
        step_defs_share = []

    step_defs = [
        ("T0_topology", "scripts/build_nextgen_clean_slate_cpu_topology_v1.py", topo_args),
        *step_defs_share,
        (
            "T1_rtt_loopback",
            "scripts/run_nextgen_clean_slate_cpu_rtt_probe_v1.py",
            ["--mode", "loopback", "--out-json", str(RTT_OUT)],
        ),
        (
            "P0_cpu_microbench",
            "scripts/run_nextgen_clean_slate_cpu_p0_microbench_v1.py",
            ["--out-json", str(P0_OUT)],
        ),
        (
            "P1_shard_ping_loopback",
            "scripts/run_nextgen_clean_slate_cpu_p1_shard_ping_v1.py",
            ["--mode", "loopback", "--out-json", str(P1_OUT)],
        ),
        (
            "P2_ng40_latent_stub_shadow",
            "scripts/run_nextgen_latent_indexer_stub_ng40_shadow_v1.py",
            ["--out-json", str(NG40_SHADOW_OUT)],
        ),
        (
            "P2b_ng40_latent_poc",
            "scripts/run_nextgen_latent_indexer_poc_ng40_v1.py",
            ["--out-json", str(NG40_POC_OUT)],
        ),
    ]

    if aux_host or aux_ip:
        host = aux_ip or aux_host or "127.0.0.1"
        insert_at = 2 + len(step_defs_share)
        step_defs.insert(
            insert_at,
            (
                "T1b_rtt_aux_client",
                "scripts/run_nextgen_clean_slate_cpu_rtt_probe_v1.py",
                [
                    "--mode",
                    "client",
                    "--host",
                    host,
                    "--rounds",
                    "3",
                    "--payload-kb",
                    "256",
                    "--out-json",
                    str(EXP / "results/rtt_probe_aux_v1_latest.json"),
                ],
                True,
                90,
            ),
        )
        step_defs.insert(
            insert_at + 1,
            (
                "P1b_shard_ping_aux_client",
                "scripts/run_nextgen_clean_slate_cpu_p1_shard_ping_v1.py",
                [
                    "--mode",
                    "client",
                    "--host",
                    host,
                    "--port",
                    "19877",
                    "--shard-index",
                    "1",
                    "--rounds",
                    "2",
                    "--payload-kb",
                    "256",
                    "--out-json",
                    str(EXP / "results/p1_shard_ping_aux_v1_latest.json"),
                ],
                True,
                30,
            ),
        )

    for item in step_defs:
        optional = False
        timeout_s = 600
        if len(item) == 5:
            step_id, script, extra, optional, timeout_s = item
        elif len(item) == 4:
            step_id, script, extra, optional = item
        else:
            step_id, script, extra = item
        row: dict[str, Any] = {"step_id": step_id, "status": "planned"}
        if not execute:
            row["status"] = "dry_run"
            steps.append(row)
            continue
        row.update(_run(script, extra, timeout_s=timeout_s))
        if row.get("timed_out"):
            row["status"] = "optional_fail" if optional else "fail"
            row["note"] = f"subprocess exceeded {timeout_s}s"
            steps.append(row)
            continue
        if optional and row["exit_code"] != 0:
            row["status"] = "optional_fail"
            row["note"] = "Start RUN_RTT_SERVER_ON_AUX.cmd on aux PC, then re-run"
        else:
            row["status"] = "ok" if row["exit_code"] == 0 else "fail"
        steps.append(row)

    topology = _load_json(TOPOLOGY)
    rtt = _load_json(RTT_OUT)
    rtt_aux = _load_json(EXP / "results/rtt_probe_aux_v1_latest.json")
    share_bus = _load_json(EXP / "results/share_bus_probe_v1_latest.json")
    p0 = _load_json(P0_OUT)
    p1 = _load_json(P1_OUT)
    ng40 = _load_json(NG40_SHADOW_OUT)
    ng40_poc = _load_json(NG40_POC_OUT)
    latency = _merged_latency(topology, rtt, rtt_aux)

    baseline = {
        "schema": "nextgen_neural_baseline_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "track_a_active_write": False,
        "hypo_label": "[HYPO]",
        "golden40_compatible": False,
        "implementation_phase": (
            "poc_cpu_distributed_v0+p2_ng40_poc"
            if ng40_poc and ng40_poc.get("golden40_compatible")
            else (
                "poc_cpu_distributed_v0+p2_ng40_shadow"
                if ng40 and ng40.get("golden40_compatible")
                else "poc_cpu_distributed_v0"
            )
        ),
        "verdict": "experimental_go_poc_v0" if execute else "planned",
        "promotion_status": "research_only",
        "frozen_baseline_parallel": _frozen_snapshot(),
        "topology_pointer": _rel(TOPOLOGY) if TOPOLOGY.is_file() else None,
        "artifacts": {
            "topology": _rel(TOPOLOGY) if TOPOLOGY.is_file() else None,
            "rtt_probe": _rel(RTT_OUT) if RTT_OUT.is_file() else None,
            "p0_microbench": _rel(P0_OUT) if P0_OUT.is_file() else None,
            "p1_shard_ping": _rel(P1_OUT) if P1_OUT.is_file() else None,
            "ng40_latent_stub_shadow": _rel(NG40_SHADOW_OUT) if NG40_SHADOW_OUT.is_file() else None,
            "ng40_latent_poc": _rel(NG40_POC_OUT) if NG40_POC_OUT.is_file() else None,
        },
        "measurements_summary": {
            "latency_verdict": latency,
            "share_bus_probe": share_bus,
            "rtt_aux": rtt_aux,
            "ng40_latent_stub_shadow": ng40,
            "ng40_latent_poc": ng40_poc,
            "p0_throughput_mb_s": (p0 or {}).get("results", {}).get("throughput_mb_s"),
            "p1_shard_elapsed_ms_p50": (p1 or {})
            .get("measurement", {})
            .get("elapsed_ms", {})
            .get("p50"),
        },
        "steps": steps,
        "guardrails": [
            "No Track A active write",
            "No live trading",
            "Golden-40 not replaced by this baseline",
        ],
    }

    if execute:
        BASELINE_OUT.parent.mkdir(parents=True, exist_ok=True)
        BASELINE_OUT.write_text(
            json.dumps(baseline, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    return {
        "schema": "nextgen_clean_slate_cpu_sandbox_chain_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "execute": execute,
        "aux_configured": bool(aux_host or aux_ip),
        "steps": steps,
        "baseline_pointer": _rel(BASELINE_OUT),
        "baseline": baseline if execute else {"status": "dry_run"},
        "nextgen_arm_status": "partial_poc" if execute else "charter_only",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--aux-host", default=None)
    ap.add_argument("--aux-ip", default=None)
    ap.add_argument(
        "--aux-share-root",
        default=None,
        help="Mapped SMB root (e.g. Z:/) — enables share bus probe + aux drop deploy",
    )
    ap.add_argument(
        "--out-json",
        type=Path,
        default=EXP / "results/sandbox_chain_v1_latest.json",
    )
    ap.add_argument(
        "--skip-aux-deploy",
        action="store_true",
        help="Skip T0b redeploy (RTT server may lock Z:\\nextgen_cpu_aux)",
    )
    ap.add_argument(
        "--main-only",
        action="store_true",
        help="Exclude aux PC: no SMB deploy, share probe, or aux RTT/P1 client steps",
    )
    args = ap.parse_args()

    execute = bool(args.execute)
    if not execute and not args.dry_run:
        args.dry_run = True

    doc = build_plan(
        execute=execute,
        aux_host=args.aux_host,
        aux_ip=args.aux_ip,
        aux_share_root=args.aux_share_root,
        skip_aux_deploy=bool(args.skip_aux_deploy),
        main_only=bool(args.main_only),
    )
    if args.main_only:
        doc["main_only"] = True
        doc["aux_excluded"] = True
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "wrote": str(args.out_json),
                "execute": execute,
                "nextgen_arm_status": doc["nextgen_arm_status"],
                "baseline": str(BASELINE_OUT) if execute else None,
            },
            ensure_ascii=False,
        )
    )
    hard_fail = any(s.get("status") == "fail" for s in doc["steps"])
    return 1 if hard_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
