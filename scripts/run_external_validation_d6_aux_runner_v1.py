#!/usr/bin/env python3
"""Aux-PC runner: execute manifest reproduce_week1; write result to share folder."""
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RESULT_NAME_DEFAULT = "aux_d6_result_v1_latest.json"
RESULT_NAME_FULL = "aux_d6_full_result_v1_latest.json"

ARTIFACT_CHECKS_DEFAULT = [
    "reports/mkm_high_delegation_preflight_v1_latest.json",
    "reports/hd_autonomous_evolution_completion_v1_latest.json",
    "reports/compression_proof_completion_chain_v1_latest.json",
    "docs/final/artifacts/edge_encoder_air_gap_poc_pack_v1_latest.json",
    "docs/final/artifacts/hybrid_b2b_commercialization_pipeline_v1_latest.json",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _git_head(root: Path) -> str:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=15,
        )
        if proc.returncode == 0:
            return (proc.stdout or "").strip()
    except Exception:
        pass
    return "unknown"


def _gate_snapshot(root: Path, fallback: dict[str, Any] | None = None) -> dict[str, Any]:
    path = root / "docs/final/artifacts/hybrid_b2b_commercialization_pipeline_v1_latest.json"
    if not path.exists():
        base = fallback or {}
        return {
            "send_gate": base.get("send_gate"),
            "ready_for_external_send": base.get("ready_for_external_send"),
            "readiness_all_ok": base.get("readiness_all_ok"),
            "gate_source": "manifest_baseline",
        }
    doc = _read_json(path)
    return {
        "send_gate": doc.get("send_gate"),
        "ready_for_external_send": doc.get("ready_for_external_send"),
        "readiness_all_ok": doc.get("readiness_all_ok"),
        "gate_source": "hybrid_artifact",
    }


def _seed_artifacts_from_share(root: Path, share: Path, rels: list[str]) -> list[dict[str, Any]]:
    seed_dir = share / "seed_artifacts"
    rows: list[dict[str, Any]] = []
    if not seed_dir.is_dir():
        return rows
    for rel in rels:
        dest = root / rel
        seed = seed_dir / Path(rel).name
        copied = False
        if seed.exists() and not dest.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(seed.read_bytes())
            copied = True
        rows.append(
            {
                "path": rel,
                "seed_exists": seed.exists(),
                "workspace_exists": dest.exists(),
                "seeded_now": copied,
            }
        )
    return rows


def _run_command(command: str, cwd: Path) -> dict[str, Any]:
    started = _utc_now()
    proc = subprocess.run(
        command,
        cwd=cwd,
        shell=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    ended = _utc_now()
    tail = ((proc.stdout or "") + (proc.stderr or "")).strip()[-400:]
    return {
        "command": command,
        "exit_code": proc.returncode,
        "started_at_utc": started,
        "ended_at_utc": ended,
        "ok": proc.returncode == 0,
        "log_tail": tail,
    }


def _artifact_presence(root: Path, rels: list[str]) -> list[dict[str, Any]]:
    return [{"path": rel, "exists": (root / rel).exists()} for rel in rels]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--share-dir", type=Path, required=True)
    ap.add_argument("--workspace-root", type=Path, default=None)
    ap.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help="Manifest JSON (default: <share-dir>/manifest.json)",
    )
    ap.add_argument(
        "--result-name",
        default=None,
        help="Result filename under share (default from manifest or aux_d6_result_v1_latest.json)",
    )
    ap.add_argument("--operator", default="auxiliary_pc_vscode")
    args = ap.parse_args()

    share = args.share_dir.resolve()
    root = Path(args.workspace_root or os.environ.get("MKM_WORKSPACE_ROOT", r"C:\workspace")).resolve()
    manifest_path = (args.manifest or (share / "manifest.json")).resolve()
    if not manifest_path.exists():
        print(json.dumps({"ok": False, "error": f"missing {manifest_path}"}))
        return 1
    if not root.exists():
        print(json.dumps({"ok": False, "error": f"workspace missing: {root}"}))
        return 1

    manifest = _read_json(manifest_path)
    commands: list[str] = list(manifest.get("reproduce_week1") or [])
    artifact_checks: list[str] = list(manifest.get("artifact_checks") or ARTIFACT_CHECKS_DEFAULT)
    expected_gate = manifest.get("gate_baseline") or {
        "send_gate": "HOLD",
        "ready_for_external_send": False,
        "readiness_all_ok": False,
    }
    apply_seeds = bool(manifest.get("apply_seeds_before_run", True))
    chain_mode = manifest.get("chain_mode") or "fallback_6step"
    rehearsal_class = manifest.get("rehearsal_class") or "true_third_party"
    result_name = args.result_name or manifest.get("result_file") or RESULT_NAME_DEFAULT
    seed_rows = (
        _seed_artifacts_from_share(root, share, artifact_checks) if apply_seeds else []
    )
    gate_before = _gate_snapshot(root, expected_gate)
    steps = [_run_command(cmd, root) for cmd in commands]
    gate_after = _gate_snapshot(root, expected_gate)
    artifacts = _artifact_presence(root, artifact_checks)
    gate_match = (
        gate_after.get("send_gate") == expected_gate.get("send_gate")
        and gate_after.get("ready_for_external_send") == expected_gate.get("ready_for_external_send")
        and gate_after.get("readiness_all_ok") == expected_gate.get("readiness_all_ok")
        and gate_before.get("send_gate") == gate_after.get("send_gate")
        and gate_before.get("ready_for_external_send") == gate_after.get("ready_for_external_send")
        and gate_before.get("readiness_all_ok") == gate_after.get("readiness_all_ok")
    )
    all_ok = bool(steps) and all(s["ok"] for s in steps) and all(a["exists"] for a in artifacts)

    report = {
        "schema": "external_validation_d6_independent_rehearsal_v1",
        "generated_at_utc": _utc_now(),
        "lane": "infra",
        "disclaimer": "internal_only",
        "rehearsal_class": rehearsal_class,
        "chain_mode": chain_mode,
        "apply_seeds_before_run": apply_seeds,
        "operator": args.operator,
        "host": socket.gethostname(),
        "workspace_root": str(root),
        "aux_git_head": _git_head(root),
        "manifest_path": str(manifest_path),
        "result_file": result_name,
        "share_dir": str(share),
        "steps": steps,
        "summary": {
            "step_count": len(steps),
            "steps_ok": sum(1 for s in steps if s.get("ok")),
            "all_steps_exit_0": all_ok and all(s["ok"] for s in steps),
            "artifacts_ok": all(a["exists"] for a in artifacts),
        },
        "gate_before": gate_before,
        "gate_after": gate_after,
        "gate_match": gate_match,
        "gate_expected": expected_gate,
        "artifact_checks": artifacts,
        "seed_artifacts": seed_rows,
        "status": "ok" if all_ok and gate_match else "fail",
    }
    out_path = share / result_name
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": report["status"] == "ok", "out": str(out_path), "status": report["status"]}))
    return 0 if report["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
