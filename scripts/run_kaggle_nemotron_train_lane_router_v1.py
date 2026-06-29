#!/usr/bin/env python3
"""Nemotron train lane router — Kaggle smoke vs bounded full vs RunPod/Lab [HYPO].

SSOT: nvidia_gpu_credit_lane_policy_v1, kaggle_private_dev_policy_v1,
nemotron_runpod_cost_guard_v1, kaggle_nemotron_resume_latest.json

Output: reports/kaggle_nemotron_train_lane_router_v1_latest.json
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/kaggle_nemotron_train_lane_router_v1_latest.json"
RESUME = ROOT / "reports/kaggle_nemotron_resume_latest.json"
GPU_POLICY = ROOT / "docs/final/artifacts/nvidia_gpu_credit_lane_policy_v1.json"
KAGGLE_POLICY = ROOT / "docs/final/artifacts/kaggle_private_dev_policy_v1.json"
COST_GUARD = ROOT / "docs/final/artifacts/nemotron_runpod_cost_guard_v1.json"
INVOKE_KAGGLE = ROOT / "scripts/Invoke-KaggleNemotronTrainOnKaggle_v1.ps1"
INVOKE_RUNPOD_FULL = ROOT / "scripts/Invoke-RunPodNemotronFull_v1.ps1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _rel(p: Path) -> str:
    try:
        return str(p.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p)


def _env_truthy(key: str) -> bool:
    val = os.environ.get(key, "").strip().lower()
    if val in ("1", "true", "yes", "on"):
        return True
    env_path = ROOT / ".env"
    if not env_path.is_file():
        return False
    for line in env_path.read_text(encoding="utf-8-sig").splitlines():
        if line.strip().startswith("#"):
            continue
        if line.split("=", 1)[0].strip() == key:
            rhs = line.split("=", 1)[1].strip().strip('"').strip("'").lower()
            return rhs in ("1", "true", "yes", "on")
    return False


def _run_ps1(script: Path, *extra: str, timeout: int = 14400) -> dict:
    cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script),
        *extra,
    ]
    cp = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    return {
        "command": " ".join(cmd),
        "exit_code": cp.returncode,
        "ok": cp.returncode == 0,
        "stdout_tail": (cp.stdout or "")[-1200:],
        "stderr_tail": (cp.stderr or "")[-800:] if cp.returncode != 0 else "",
    }


def _run_local_kaggle_validate(prep_limit: int, dryrun_limit: int) -> dict:
    return _run_ps1(
        INVOKE_KAGGLE,
        "-PrepLimit",
        str(prep_limit),
        "-DryRunLimit",
        str(dryrun_limit),
        timeout=900,
    )


def _run_kaggle_remote(*, kaggle_full: bool, wait: bool) -> dict:
    args = [
        "-AllowKernelPush",
        "-TrainProfile",
        "nemotron",
        "-Accelerator",
        "gpu-t4-x2",
    ]
    if kaggle_full:
        args.append("-KaggleFull")
    if wait:
        args.append("-WaitForKernelComplete")
    result = _run_ps1(INVOKE_KAGGLE, *args, timeout=14400)
    result["kaggle_full"] = kaggle_full
    result["kernel_wait"] = wait
    resume_after = _read_json(RESUME)
    result["kernel_final_status"] = resume_after.get("kernel_final_status")
    result["poll_degraded"] = resume_after.get("kernel_final_status") == "poll_degraded"
    if wait and result.get("ok") and result.get("poll_degraded"):
        result["note_ko"] = "push OK · Kaggle status API 500 — UI에서 COMPLETE 확인 필요"
    return result


def _run_runpod_phase(full_limit: int) -> dict:
    if not _env_truthy("GO_RUNPOD"):
        handoff = _run_ps1(
            INVOKE_RUNPOD_FULL,
            "-FullLimit",
            str(full_limit),
            timeout=600,
        )
        return {
            "status": "blocked_no_go_runpod",
            "ok": handoff.get("ok", False),
            "note_ko": "GO_RUNPOD 미설정 — handoff/pack만 생성. 실제 Pod 기동은 지휘관 승인 후.",
            "handoff": handoff,
            "requires": "GO_RUNPOD=1 in .env + cost guard sign-off",
        }
    result = _run_ps1(
        INVOKE_RUNPOD_FULL,
        "-FullLimit",
        str(full_limit),
        timeout=600,
    )
    return {
        "status": "handoff_executed_with_go_runpod",
        "ok": result.get("ok", False),
        "note_ko": "GO_RUNPOD 설정됨 — handoff 갱신. SSH/Pod 기동은 별도 PodSsh 인자.",
        "handoff": result,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Nemotron train lane router v1 [HYPO]")
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--execute-local-validate",
        action="store_true",
        help="Run Phase A only (no push)",
    )
    ap.add_argument(
        "--execute-sequential",
        action="store_true",
        help="Run Phase A→B→C→D→E in order (B/C wait for Kaggle COMPLETE)",
    )
    ap.add_argument("--skip-phase-a", action="store_true")
    ap.add_argument("--prep-limit", type=int, default=32)
    ap.add_argument("--dryrun-limit", type=int, default=8)
    ap.add_argument("--strict", action="store_true", help="exit 1 if any executed phase fails")
    args = ap.parse_args()

    gpu = _read_json(GPU_POLICY)
    kaggle_pol = _read_json(KAGGLE_POLICY)
    guard = _read_json(COST_GUARD)
    resume = _read_json(RESUME)

    lab_lane = (gpu.get("lanes") or {}).get("train_cloud_innovation_lab") or {}
    kaggle_lane = (gpu.get("lanes") or {}).get("kaggle_gpu") or {}
    runpod_full_ok = ((resume.get("runpod_cloud_full") or {}).get("status") == "ok")
    expansion = resume.get("expansion_stance") or guard.get("expansion_stance_default") or "HOLD"
    full_limit = guard.get("limits", {}).get("default_full_limit_rows", 2048)

    phases = {
        "A_kaggle_local_validate": {
            "purpose_ko": "노트북 sync · prep · train dry-run · Kaggle API probe (push 없음)",
            "command": (
                f"powershell -NoProfile -ExecutionPolicy Bypass -File {_rel(INVOKE_KAGGLE)} "
                f"-PrepLimit {args.prep_limit} -DryRunLimit {args.dryrun_limit}"
            ),
            "human_gate": False,
            "long_train": False,
        },
        "B_kaggle_smoke_remote": {
            "purpose_ko": "T4 x2 스모크 1회 (주간 quota 소모)",
            "command": (
                f"powershell -NoProfile -ExecutionPolicy Bypass -File {_rel(INVOKE_KAGGLE)} "
                "-AllowKernelPush -TrainProfile nemotron -WaitForKernelComplete -Accelerator gpu-t4-x2"
            ),
            "human_gate": True,
            "long_train": False,
            "kernel_url": kaggle_lane.get("kernel_id_notebook")
            or resume.get("kernel_url")
            or "https://www.kaggle.com/code/familyunion/nemotron-qlora-private-train-v2-notebook-t4",
            "manual_checks_ko": [
                "Kaggle Secrets: HF_TOKEN",
                "Settings → GPU T4 x2 (P100 차단)",
                "Private · Submit 금지",
            ],
        },
        "C_kaggle_bounded_full": {
            "purpose_ko": "단일 세션 MKM_KAGGLE_FULL=1 (~9500 row) — 장기 훈련 아님",
            "command": (
                f"powershell -NoProfile -ExecutionPolicy Bypass -File {_rel(INVOKE_KAGGLE)} "
                "-AllowKernelPush -TrainProfile nemotron -KaggleFull -WaitForKernelComplete "
                "-Accelerator gpu-t4-x2"
            ),
            "long_train_on_kaggle": False,
            "note_ko": "세션 9–12h·주간 quota·working 20GB 한도. 며칠 연속 불가.",
            "notebook_env": "MKM_KAGGLE_FULL=1",
            "human_gate": True,
        },
        "D_runpod_full_proven": {
            "purpose_ko": "장시간·다일 30B QLoRA 본선 (레포 실증 경로)",
            "command": f"powershell -NoProfile -ExecutionPolicy Bypass -File {_rel(INVOKE_RUNPOD_FULL)}",
            "proven_in_resume": runpod_full_ok,
            "expansion_stance": expansion,
            "cost_guard": _rel(COST_GUARD),
            "active_now": guard.get("active_now", False),
            "human_gate": True,
            "requires": "GO_RUNPOD + cost guard sign-off",
            "default_full_limit_rows": full_limit,
        },
        "E_innovation_lab_brev": {
            "purpose_ko": "NVIDIA GPU credits 장기 train (승인 후)",
            "status": lab_lane.get("status", "unknown"),
            "active_now": lab_lane.get("active_now", False),
            "pointer": lab_lane.get("pointer"),
            "human_gate": True,
        },
    }

    executed_failures: list[str] = []

    if args.execute_sequential:
        if not args.skip_phase_a:
            local_result = _run_local_kaggle_validate(args.prep_limit, args.dryrun_limit)
            phases["A_kaggle_local_validate"]["executed"] = local_result
            if not local_result.get("ok"):
                executed_failures.append("A")

        smoke = _run_kaggle_remote(kaggle_full=False, wait=True)
        phases["B_kaggle_smoke_remote"]["executed"] = smoke
        if not smoke.get("ok"):
            executed_failures.append("B")
        elif smoke.get("poll_degraded"):
            phases["B_kaggle_smoke_remote"]["poll_degraded"] = True

        bounded = _run_kaggle_remote(kaggle_full=True, wait=True)
        phases["C_kaggle_bounded_full"]["executed"] = bounded
        if not bounded.get("ok"):
            executed_failures.append("C")
        elif bounded.get("poll_degraded"):
            phases["C_kaggle_bounded_full"]["poll_degraded"] = True

        runpod = _run_runpod_phase(full_limit)
        phases["D_runpod_full_proven"]["executed"] = runpod
        if runpod.get("status") == "blocked_no_go_runpod":
            phases["D_runpod_full_proven"]["skipped_reason"] = "GO_RUNPOD not set"
        elif not runpod.get("ok"):
            executed_failures.append("D")

        phases["E_innovation_lab_brev"]["executed"] = {
            "status": lab_lane.get("status", "unknown"),
            "active_now": lab_lane.get("active_now", False),
            "ok": not lab_lane.get("active_now", False),
            "note_ko": "Innovation Lab 미활성 — 대기만 기록.",
        }

    elif args.execute_local_validate:
        local_result = _run_local_kaggle_validate(args.prep_limit, args.dryrun_limit)
        phases["A_kaggle_local_validate"]["executed"] = local_result
        if not local_result.get("ok"):
            executed_failures.append("A")

    if runpod_full_ok and expansion == "HOLD":
        recommended = (
            "HOLD: RunPod full already proven (see kaggle_nemotron_resume_latest). "
            "Kaggle = smoke/validate only. Re-open RunPod mid-scale only with GO_RUNPOD."
        )
        next_command = phases["A_kaggle_local_validate"]["command"]
    elif lab_lane.get("active_now"):
        recommended = "Innovation Lab active — migrate full train off Kaggle."
        next_command = phases["E_innovation_lab_brev"].get("pointer") or ""
    elif args.execute_sequential and not executed_failures:
        recommended = "Sequential phases A–E completed (D may be handoff-only without GO_RUNPOD)."
        next_command = phases["D_runpod_full_proven"]["command"]
    else:
        recommended = "Phase A local validate → optional B smoke; long train → Phase D RunPod (not Kaggle)."
        next_command = phases["A_kaggle_local_validate"]["command"]

    doc = {
        "schema": "kaggle_nemotron_train_lane_router_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "wired_into_train": False,
        "track_wall": "no_track_a_live_auto_merge",
        "long_train_on_kaggle": False,
        "long_train_recommendation_ko": (
            "Kaggle 장기 훈련 비권장. 스모크/단일세션 bounded full만. "
            "본격 multi-day → RunPod(실증) 또는 Innovation Lab(승인 후)."
        ),
        "policy_paths": {
            "gpu_credit_lane": _rel(GPU_POLICY),
            "kaggle_private_dev": _rel(KAGGLE_POLICY),
            "runpod_cost_guard": _rel(COST_GUARD),
            "resume": _rel(RESUME),
        },
        "resume_snapshot": {
            "expansion_stance": expansion,
            "runpod_cloud_full_ok": runpod_full_ok,
            "runpod_row_count": (resume.get("runpod_cloud_full") or {}).get("row_count"),
            "kaggle_lane_status": kaggle_lane.get("status"),
            "allow_competition_submit": kaggle_pol.get("allow_competition_submit", False),
        },
        "phases": phases,
        "sequential_executed": args.execute_sequential,
        "executed_failures": executed_failures,
        "recommended_next": recommended,
        "next_command": next_command,
        "forbidden": [
            "Track A promotion from train output",
            "live trading GO",
            "competition auto-submit",
            "69k rows without cost guard sign-off",
        ],
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    payload = {
        "ok": len(executed_failures) == 0,
        "out": str(args.out_json),
        "long_train_on_kaggle": False,
        "recommended_next": recommended,
        "executed_failures": executed_failures,
    }
    print(json.dumps(payload, ensure_ascii=False))

    if args.strict and executed_failures:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
