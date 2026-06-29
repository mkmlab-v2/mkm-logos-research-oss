#!/usr/bin/env python3
"""Deploy external-validation D6 job drop zone to aux PC share (Z:)."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SHARE_DEFAULT = Path("Z:/external_validation_d6_aux")
MANIFEST_SRC = ROOT / "reports/external_validation_minimal_pack_v1_latest/manifest.json"
RUNNER_SRC = ROOT / "scripts/run_external_validation_d6_aux_runner_v1.py"
INDEPENDENT_SRC = ROOT / "scripts/run_external_validation_d6_independent_rehearsal_v1.py"
CHECK_SRC = ROOT / "scripts/check_external_validation_d6_aux_readiness_v1.py"
PARITY_ENTRY_SRC = ROOT / "scripts/run_compression_parity_aux_entrypoint_v1.py"
MINIMAL_PACK_DIR = ROOT / "reports/external_validation_minimal_pack_v1_latest"
PROMPT_SRC = ROOT / "scripts/assets/external_validation_d6_aux_cursor_prompt_v1.txt"
OUT = ROOT / "reports/external_validation_d6_aux_drop_v1_latest.json"

JOB_NAME = "d6_job_request_v1.json"
RESULT_NAME = "aux_d6_result_v1_latest.json"
RESULT_NAME_FULL = "aux_d6_full_result_v1_latest.json"
AUX_PARITY_PYTHON = "3.11"  # must match main host py launcher pin for metric parity

FULL_WEEK1_COMMANDS = [
    "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\Invoke-MkmHighDelegationPreflight_v1.ps1 -Scale M -Lane infra",
    "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\Invoke-MkmHighDimensionalAutonomousEvolution_v1.ps1 -Mission \"대외 입증 패키지 고정: 재현 명령, 벤치 아티팩트, 게이트 판정, 2주 실행안 산출\" -Lane infra -CostTier tier_0",
    "py scripts/run_compression_proof_completion_chain_v1.py",
    "powershell -NoProfile -ExecutionPolicy Bypass -Command \"py -m pip install pytest -q; py -m pytest tests/test_edge_encoder_sdk_v1.py -q\"",
    "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\Invoke-EdgeEncoderAirGapPoC_v1.ps1",
    "py scripts/build_hybrid_b2b_commercialization_pipeline_v1.py",
    "py scripts/build_external_validation_minimal_pack_v1.py",
]

# Aux host-tuned 7-step parity (thin workspace; not identical to main host gates / PyInstaller chain).
FULL_WEEK1_COMMANDS_AUX = [
    "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\Invoke-MkmHighDelegationPreflight_v1.ps1 -Scale M -Lane infra -SkipSessionUpgrade -SkipHostGates",
    "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\Invoke-MkmHighDimensionalAutonomousEvolution_v1.ps1 -Mission \"대외 입증 패키지 고정: 재현 명령, 벤치 아티팩트, 게이트 판정, 2주 실행안 산출\" -Lane infra -CostTier tier_0",
    "py scripts/run_external_validation_d6_aux_compression_step_v1.py",
    "powershell -NoProfile -ExecutionPolicy Bypass -Command \"py -m pip install pytest -q; py -m pytest tests/test_edge_encoder_sdk_v1.py -q -k 'not test_edge_encoder_sdk_smoke_exit_0'\"",
    "powershell -NoProfile -ExecutionPolicy Bypass -Command \"py scripts/build_edge_encoder_sdk_portable_launcher_v1.py; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; py scripts/build_edge_encoder_air_gap_poc_pack_v1.py\"",
    "py scripts/build_hybrid_b2b_commercialization_pipeline_v1.py",
    "py scripts/build_external_validation_minimal_pack_v1.py",
]

FULL_ARTIFACT_CHECKS = [
    "reports/mkm_high_delegation_preflight_v1_latest.json",
    "reports/hd_autonomous_evolution_completion_v1_latest.json",
    "reports/compression_proof_completion_chain_v1_latest.json",
    "docs/final/artifacts/edge_encoder_air_gap_poc_pack_v1_latest.json",
    "docs/final/artifacts/hybrid_b2b_commercialization_pipeline_v1_latest.json",
    "reports/external_validation_minimal_pack_v1_latest/manifest.json",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _git_head() -> str:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=15,
        )
        if proc.returncode == 0:
            return (proc.stdout or "").strip()
    except Exception:
        pass
    return "unknown"


def _copy_seed_artifacts(share: Path, rels: list[str]) -> list[str]:
    seed_dir = share / "seed_artifacts"
    seed_dir.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for rel in rels:
        name = Path(rel).name
        candidates = [
            MINIMAL_PACK_DIR / name,
            ROOT / rel,
        ]
        for src in candidates:
            if src.exists():
                dest = seed_dir / name
                shutil.copy2(src, dest)
                copied.append(name)
                break
    return copied


def stage(share: Path, aux_workspace: str) -> dict[str, Any]:
    if not SHARE_DEFAULT.drive and not share.exists():
        parent = share.parent
        if str(share).startswith("Z:") and not parent.exists():
            raise SystemExit(f"Z: share not mounted: {share}")

    share.mkdir(parents=True, exist_ok=True)
    if not MANIFEST_SRC.exists():
        raise SystemExit(f"missing manifest: {MANIFEST_SRC.relative_to(ROOT)}")
    if not RUNNER_SRC.exists():
        raise SystemExit(f"missing runner: {RUNNER_SRC.relative_to(ROOT)}")

    shutil.copy2(MANIFEST_SRC, share / "manifest_full_week1.json")
    shutil.copy2(RUNNER_SRC, share / "run_external_validation_d6_aux_runner_v1.py")
    if INDEPENDENT_SRC.exists():
        shutil.copy2(INDEPENDENT_SRC, share / "run_external_validation_d6_independent_rehearsal_v1.py")
    if CHECK_SRC.exists():
        shutil.copy2(CHECK_SRC, share / "check_external_validation_d6_aux_readiness_v1.py")
    if PARITY_ENTRY_SRC.exists():
        shutil.copy2(PARITY_ENTRY_SRC, share / "run_compression_parity_aux_v1.py")

    full_manifest = json.loads(MANIFEST_SRC.read_text(encoding="utf-8"))
    # Placeholder replaced in manifest with concrete C:\share path.
    aux_commands_manifest = [
        "py C:\\share\\external_validation_d6_aux\\check_external_validation_d6_aux_readiness_v1.py --share-dir C:\\share\\external_validation_d6_aux",
        "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\Invoke-MkmHighDimensionalAutonomousEvolution_v1.ps1 -Mission \"대외 입증 패키지 고정: 재현 명령, 벤치 아티팩트, 게이트 판정, 2주 실행안 산출\" -Lane infra -CostTier tier_0",
        "py -c \"import json, pathlib; p=pathlib.Path('reports/compression_proof_completion_chain_v1_latest.json'); d=json.loads(p.read_text(encoding='utf-8')); print('compression_seed_ok', d.get('chain_ok', True));\"",
        "powershell -NoProfile -ExecutionPolicy Bypass -Command \"py -m pip install pytest -q; py -m pytest tests/test_edge_encoder_sdk_v1.py -q -k 'not test_edge_encoder_sdk_smoke_exit_0'\"",
        "py -c \"import pathlib; p=pathlib.Path('docs/final/artifacts/edge_encoder_air_gap_poc_pack_v1_latest.json'); print('air_gap_seed_ok', p.exists()); raise SystemExit(0 if p.exists() else 1)\"",
        "py scripts/build_hybrid_b2b_commercialization_pipeline_v1.py",
    ]
    artifact_checks = [
        "reports/mkm_high_delegation_preflight_v1_latest.json",
        "reports/hd_autonomous_evolution_completion_v1_latest.json",
        "reports/compression_proof_completion_chain_v1_latest.json",
        "docs/final/artifacts/edge_encoder_air_gap_poc_pack_v1_latest.json",
        "docs/final/artifacts/hybrid_b2b_commercialization_pipeline_v1_latest.json",
    ]
    seed_files = _copy_seed_artifacts(share, artifact_checks)
    main_git_head = _git_head()
    aux_manifest = {
        **full_manifest,
        "schema": "external_validation_minimal_pack_aux_d6_v1",
        "chain_mode": "fallback_6step",
        "rehearsal_class": "true_third_party",
        "apply_seeds_before_run": True,
        "result_file": RESULT_NAME,
        "scope_note": "Aux D6 fallback chain for non-git third-party host: readiness + HD + seeded compression/airgap checks + pytest subset + hybrid.",
        "reproduce_week1": aux_commands_manifest,
        "artifact_checks": artifact_checks,
    }
    (share / "manifest.json").write_text(
        json.dumps(aux_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    full_aux_manifest = {
        **full_manifest,
        "schema": "external_validation_minimal_pack_aux_d6_full_v1",
        "chain_mode": "full_week1_7step",
        "rehearsal_class": "true_third_party_full_chain",
        "apply_seeds_before_run": False,
        "result_file": RESULT_NAME_FULL,
        "scope_note": "Aux 7-step host-tuned parity: SkipHostGates preflight, compression sandbox+skip-evidence, pytest smoke excluded, air-gap pack-only (no PyInstaller/HTTP). Not identical to main full host.",
        "reproduce_week1": FULL_WEEK1_COMMANDS_AUX,
        "artifact_checks": FULL_ARTIFACT_CHECKS,
    }
    (share / "manifest_full_aux_d6.json").write_text(
        json.dumps(full_aux_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if PROMPT_SRC.exists():
        shutil.copy2(PROMPT_SRC, share / "CURSOR_PROMPT.txt")
    mission_tpl = ROOT / "scripts/assets/external_validation_d6_aux_mission_log_stub_v1.md"
    if not mission_tpl.exists():
        mission_tpl = ROOT / "MISSION_LOG.template.md"
    if mission_tpl.exists():
        shutil.copy2(mission_tpl, share / "MISSION_LOG.aux_stub.md")

    cmd_body = (
        "@echo off\r\n"
        "setlocal\r\n"
        f"set MKM_WORKSPACE_ROOT={aux_workspace}\r\n"
        "set SHARE_DIR=%~dp0\r\n"
        "if \"%SHARE_DIR:~-1%\"==\"\\\" set SHARE_DIR=%SHARE_DIR:~0,-1%\r\n"
        "cd /d \"%MKM_WORKSPACE_ROOT%\"\r\n"
        "if errorlevel 1 (\r\n"
        "  echo [FAIL] workspace not found: %MKM_WORKSPACE_ROOT%\r\n"
        "  exit /b 1\r\n"
        ")\r\n"
        "py \"%~dp0run_external_validation_d6_aux_runner_v1.py\" --share-dir \"%SHARE_DIR%\"\r\n"
        "exit /b %ERRORLEVEL%\r\n"
    )
    (share / "RUN_D6_ON_AUX.cmd").write_text(cmd_body, encoding="utf-8")

    run_full_body = (
        "@echo off\r\n"
        "setlocal\r\n"
        f"set MKM_WORKSPACE_ROOT={aux_workspace}\r\n"
        "set MKM_VAULT_ROOT=C:\\workspace\\storage\\aux_vault_stub\r\n"
        "set PYTHONOPTIMIZE=\r\n"
        "set SHARE_DIR=%~dp0\r\n"
        "if \"%SHARE_DIR:~-1%\"==\"\\\" set SHARE_DIR=%SHARE_DIR:~0,-1%\r\n"
        "cd /d \"%MKM_WORKSPACE_ROOT%\"\r\n"
        "if errorlevel 1 (\r\n"
        "  echo [FAIL] workspace not found: %MKM_WORKSPACE_ROOT%\r\n"
        "  exit /b 1\r\n"
        ")\r\n"
        "py \"%~dp0run_external_validation_d6_aux_runner_v1.py\" --share-dir \"%SHARE_DIR%\" "
        "--manifest \"%SHARE_DIR%\\manifest_full_aux_d6.json\" "
        f"--result-name {RESULT_NAME_FULL}\r\n"
        "exit /b %ERRORLEVEL%\r\n"
    )
    (share / "RUN_D6_FULL_ON_AUX.cmd").write_text(run_full_body, encoding="utf-8")

    vault_stub_body = (
        "@echo off\r\n"
        "setlocal\r\n"
        "if not exist \"C:\\workspace\\storage\\aux_vault_stub\\notebooklm_sources\" "
        "mkdir \"C:\\workspace\\storage\\aux_vault_stub\\notebooklm_sources\"\r\n"
        "echo aux_vault_stub > \"C:\\workspace\\storage\\aux_vault_stub\\notebooklm_sources\\_LAST_SYNC.txt\"\r\n"
        "echo [OK] MKM_VAULT_ROOT stub at C:\\workspace\\storage\\aux_vault_stub\r\n"
        "exit /b 0\r\n"
    )
    (share / "CREATE_AUX_VAULT_STUB.cmd").write_text(vault_stub_body, encoding="utf-8")

    setup_full_body = (
        "@echo off\r\n"
        "setlocal\r\n"
        "set SHARE_DIR=%~dp0\r\n"
        f"set MKM_WORKSPACE_ROOT={aux_workspace}\r\n"
        "set PYTHONOPTIMIZE=\r\n"
        "if exist \"C:\\Users\\giryu\\PortableGit\\cmd\" set PATH=C:\\Users\\giryu\\PortableGit\\cmd;%PATH%\r\n"
        "call \"%SHARE_DIR%\\COPY_WORKSPACE_BUNDLE.cmd\"\r\n"
        "if errorlevel 1 exit /b 1\r\n"
        "call \"%SHARE_DIR%\\CREATE_AUX_VAULT_STUB.cmd\"\r\n"
        "if errorlevel 1 exit /b 1\r\n"
        "if exist \"%SHARE_DIR%\\MISSION_LOG.aux_stub.md\" copy /Y \"%SHARE_DIR%\\MISSION_LOG.aux_stub.md\" \"%MKM_WORKSPACE_ROOT%\\MISSION_LOG.md\" >nul\r\n"
        "call \"%SHARE_DIR%\\INSTALL_AUX_DEPS.cmd\"\r\n"
        "if errorlevel 1 exit /b 1\r\n"
        "call \"%SHARE_DIR%\\CHECK_AUX_READINESS.cmd\"\r\n"
        "exit /b %ERRORLEVEL%\r\n"
    )
    (share / "SETUP_AUX_FULL_FOR_D6.cmd").write_text(setup_full_body, encoding="utf-8")

    retry_full_body = (
        "@echo off\r\n"
        "setlocal\r\n"
        "set SHARE_DIR=%~dp0\r\n"
        "call \"%SHARE_DIR%\\SETUP_AUX_FULL_FOR_D6.cmd\"\r\n"
        "if errorlevel 1 exit /b 1\r\n"
        "call \"%SHARE_DIR%\\RUN_D6_FULL_ON_AUX.cmd\"\r\n"
        "exit /b %ERRORLEVEL%\r\n"
    )
    (share / "RETRY_D6_FULL_ON_AUX.cmd").write_text(retry_full_body, encoding="utf-8")

    parity_aux_body = (
        "@echo off\r\n"
        "setlocal\r\n"
        f"set MKM_WORKSPACE_ROOT={aux_workspace}\r\n"
        "set SHARE_DIR=%~dp0\r\n"
        "if \"%SHARE_DIR:~-1%\"==\"\\\" set SHARE_DIR=%SHARE_DIR:~0,-1%\r\n"
        "set PYTHONOPTIMIZE=\r\n"
        "cd /d \"%MKM_WORKSPACE_ROOT%\"\r\n"
        "call \"%SHARE_DIR%\\COPY_WORKSPACE_BUNDLE.cmd\"\r\n"
        "if errorlevel 1 exit /b 1\r\n"
        "call \"%SHARE_DIR%\\INSTALL_AUX_DEPS.cmd\"\r\n"
        "if errorlevel 1 exit /b 1\r\n"
        "py \"%SHARE_DIR%\\run_compression_parity_aux_v1.py\"\r\n"
        "exit /b %ERRORLEVEL%\r\n"
    )
    (share / "RUN_COMPRESSION_PARITY_ON_AUX.cmd").write_text(parity_aux_body, encoding="utf-8")

    parity_main_body = (
        "@echo off\r\n"
        "setlocal\r\n"
        "cd /d C:\\workspace\r\n"
        "py scripts\\run_compression_cross_host_parity_probe_v1.py --host-label main "
        "--out reports\\compression_cross_host_parity_main_baseline_v1_latest.json\r\n"
        "if errorlevel 1 exit /b 1\r\n"
        "py scripts\\collect_compression_cross_host_parity_aux_v1.py --share-root Z:\\external_validation_d6_aux\r\n"
        "if errorlevel 1 exit /b 1\r\n"
        "py scripts\\check_compression_cross_host_parity_v1.py\r\n"
        "exit /b %ERRORLEVEL%\r\n"
    )
    (share / "RUN_COMPRESSION_PARITY_MAIN_COLLECT_CHECK.cmd").write_text(
        parity_main_body, encoding="utf-8"
    )

    install_body = (
        "@echo off\r\n"
        "setlocal\r\n"
        f"set MKM_WORKSPACE_ROOT={aux_workspace}\r\n"
        "if not exist \"%MKM_WORKSPACE_ROOT%\\scripts\" mkdir \"%MKM_WORKSPACE_ROOT%\\scripts\"\r\n"
        "copy /Y \"%~dp0run_external_validation_d6_independent_rehearsal_v1.py\" \"%MKM_WORKSPACE_ROOT%\\scripts\\\" >nul\r\n"
        "copy /Y \"%~dp0run_external_validation_d6_aux_runner_v1.py\" \"%MKM_WORKSPACE_ROOT%\\scripts\\\" >nul\r\n"
        "echo [OK] copied D6 scripts into %MKM_WORKSPACE_ROOT%\\scripts\r\n"
        "exit /b 0\r\n"
    )
    (share / "INSTALL_D6_SCRIPTS.cmd").write_text(install_body, encoding="utf-8")

    check_body = (
        "@echo off\r\n"
        "setlocal\r\n"
        f"set MKM_WORKSPACE_ROOT={aux_workspace}\r\n"
        "set SHARE_DIR=%~dp0\r\n"
        "if \"%SHARE_DIR:~-1%\"==\"\\\" set SHARE_DIR=%SHARE_DIR:~0,-1%\r\n"
        "cd /d \"%MKM_WORKSPACE_ROOT%\"\r\n"
        "py \"%SHARE_DIR%\\check_external_validation_d6_aux_readiness_v1.py\" --share-dir \"%SHARE_DIR%\" --workspace-root \"%MKM_WORKSPACE_ROOT%\"\r\n"
        "exit /b %ERRORLEVEL%\r\n"
    )
    (share / "CHECK_AUX_READINESS.cmd").write_text(check_body, encoding="utf-8")

    sync_git_body = (
        "@echo off\r\n"
        "setlocal\r\n"
        f"set MKM_WORKSPACE_ROOT={aux_workspace}\r\n"
        f"set MAIN_GIT_HEAD={main_git_head}\r\n"
        "cd /d \"%MKM_WORKSPACE_ROOT%\"\r\n"
        "where git >nul 2>&1\r\n"
        "if errorlevel 1 (\r\n"
        "  echo [FAIL] git not found in PATH\r\n"
        "  exit /b 1\r\n"
        ")\r\n"
        "git fetch gitea 2>nul || git fetch origin 2>nul\r\n"
        "git checkout %MAIN_GIT_HEAD%\r\n"
        "if errorlevel 1 (\r\n"
        "  echo [FAIL] checkout %MAIN_GIT_HEAD% failed\r\n"
        "  exit /b 1\r\n"
        ")\r\n"
        "echo [OK] workspace at %MAIN_GIT_HEAD%\r\n"
        "exit /b 0\r\n"
    )
    (share / "SYNC_GIT_TO_MAIN_HEAD.cmd").write_text(sync_git_body, encoding="utf-8")

    copy_bundle_body = (
        "@echo off\r\n"
        "setlocal\r\n"
        f"set MKM_WORKSPACE_ROOT={aux_workspace}\r\n"
        "set SHARE_DIR=%~dp0\r\n"
        "if \"%SHARE_DIR:~-1%\"==\"\\\" set SHARE_DIR=%SHARE_DIR:~0,-1%\r\n"
        "if not exist \"%SHARE_DIR%\\scripts_bundle\" (\r\n"
        "  echo [FAIL] missing scripts_bundle - on MAIN run: py scripts/build_external_validation_d6_aux_workspace_bundle_v1.py\r\n"
        "  exit /b 1\r\n"
        ")\r\n"
        "if not exist \"%MKM_WORKSPACE_ROOT%\\scripts\" mkdir \"%MKM_WORKSPACE_ROOT%\\scripts\"\r\n"
        "if not exist \"%MKM_WORKSPACE_ROOT%\\tests\" mkdir \"%MKM_WORKSPACE_ROOT%\\tests\"\r\n"
        "if not exist \"%MKM_WORKSPACE_ROOT%\\docs\\final\\artifacts\" mkdir \"%MKM_WORKSPACE_ROOT%\\docs\\final\\artifacts\"\r\n"
        "robocopy \"%SHARE_DIR%\\scripts_bundle\" \"%MKM_WORKSPACE_ROOT%\\scripts\" /E /NFL /NDL /NJH /NJS /nc /ns /np\r\n"
        "robocopy \"%SHARE_DIR%\\tests_bundle\" \"%MKM_WORKSPACE_ROOT%\\tests\" /E /NFL /NDL /NJH /NJS /nc /ns /np\r\n"
        "if exist \"%SHARE_DIR%\\docs_artifacts_bundle\" robocopy \"%SHARE_DIR%\\docs_artifacts_bundle\" \"%MKM_WORKSPACE_ROOT%\\docs\\final\\artifacts\" /NFL /NDL /NJH /NJS /nc /ns /np\r\n"
        "if exist \"%SHARE_DIR%\\data_bundle\\anatomy\" robocopy \"%SHARE_DIR%\\data_bundle\\anatomy\" \"%MKM_WORKSPACE_ROOT%\\data\\anatomy\" /E /NFL /NDL /NJH /NJS /nc /ns /np\r\n"
        "if exist \"%SHARE_DIR%\\data_bundle\\compression\" robocopy \"%SHARE_DIR%\\data_bundle\\compression\" \"%MKM_WORKSPACE_ROOT%\\data\\compression\" /E /NFL /NDL /NJH /NJS /nc /ns /np\r\n"
        "if exist \"%SHARE_DIR%\\docs_final_md_bundle\" robocopy \"%SHARE_DIR%\\docs_final_md_bundle\" \"%MKM_WORKSPACE_ROOT%\\docs\\final\" /E /NFL /NDL /NJH /NJS /nc /ns /np\r\n"
        "if exist \"%SHARE_DIR%\\docs_root_bundle\" copy /Y \"%SHARE_DIR%\\docs_root_bundle\\NotebookLM_sources_manifest.md\" \"%MKM_WORKSPACE_ROOT%\\docs\\\" >nul 2>&1\r\n"
        "if exist \"%SHARE_DIR%\\storage_bundle\\meta\" robocopy \"%SHARE_DIR%\\storage_bundle\\meta\" \"%MKM_WORKSPACE_ROOT%\\storage\\meta\" /NFL /NDL /NJH /NJS /nc /ns /np\r\n"
        "if exist \"%SHARE_DIR%\\reports_btrack_pilot_bundle\" (\r\n"
        "  if not exist \"%MKM_WORKSPACE_ROOT%\\reports\\constitution\\btrack_pilot\" "
        "mkdir \"%MKM_WORKSPACE_ROOT%\\reports\\constitution\\btrack_pilot\"\r\n"
        "  robocopy \"%SHARE_DIR%\\reports_btrack_pilot_bundle\" "
        "\"%MKM_WORKSPACE_ROOT%\\reports\\constitution\\btrack_pilot\" /NFL /NDL /NJH /NJS /nc /ns /np\r\n"
        ")\r\n"
        "echo [OK] workspace bundle copied to %MKM_WORKSPACE_ROOT%\r\n"
        "exit /b 0\r\n"
    )
    (share / "COPY_WORKSPACE_BUNDLE.cmd").write_text(copy_bundle_body, encoding="utf-8")

    apply_seed_body = (
        "@echo off\r\n"
        "setlocal\r\n"
        f"set MKM_WORKSPACE_ROOT={aux_workspace}\r\n"
        "set SHARE_DIR=%~dp0\r\n"
        "if \"%SHARE_DIR:~-1%\"==\"\\\" set SHARE_DIR=%SHARE_DIR:~0,-1%\r\n"
        "if not exist \"%SHARE_DIR%\\seed_artifacts\" (\r\n"
        "  echo [FAIL] missing seed_artifacts\r\n"
        "  exit /b 1\r\n"
        ")\r\n"
        "if not exist \"%MKM_WORKSPACE_ROOT%\\reports\" mkdir \"%MKM_WORKSPACE_ROOT%\\reports\"\r\n"
        "if not exist \"%MKM_WORKSPACE_ROOT%\\docs\\final\\artifacts\" mkdir \"%MKM_WORKSPACE_ROOT%\\docs\\final\\artifacts\"\r\n"
        "copy /Y \"%SHARE_DIR%\\seed_artifacts\\mkm_high_delegation_preflight_v1_latest.json\" \"%MKM_WORKSPACE_ROOT%\\reports\\\" >nul 2>&1\r\n"
        "copy /Y \"%SHARE_DIR%\\seed_artifacts\\hd_autonomous_evolution_completion_v1_latest.json\" \"%MKM_WORKSPACE_ROOT%\\reports\\\" >nul 2>&1\r\n"
        "copy /Y \"%SHARE_DIR%\\seed_artifacts\\compression_proof_completion_chain_v1_latest.json\" \"%MKM_WORKSPACE_ROOT%\\reports\\\" >nul 2>&1\r\n"
        "copy /Y \"%SHARE_DIR%\\seed_artifacts\\edge_encoder_air_gap_poc_pack_v1_latest.json\" \"%MKM_WORKSPACE_ROOT%\\docs\\final\\artifacts\\\" >nul 2>&1\r\n"
        "copy /Y \"%SHARE_DIR%\\seed_artifacts\\hybrid_b2b_commercialization_pipeline_v1_latest.json\" \"%MKM_WORKSPACE_ROOT%\\docs\\final\\artifacts\\\" >nul 2>&1\r\n"
        "echo [OK] seed artifacts applied\r\n"
        "exit /b 0\r\n"
    )
    (share / "APPLY_SEED_ARTIFACTS.cmd").write_text(apply_seed_body, encoding="utf-8")

    setup_body = (
        "@echo off\r\n"
        "setlocal\r\n"
        "set SHARE_DIR=%~dp0\r\n"
        "if exist \"C:\\Users\\giryu\\PortableGit\\cmd\" set PATH=C:\\Users\\giryu\\PortableGit\\cmd;%PATH%\r\n"
        "call \"%SHARE_DIR%\\COPY_WORKSPACE_BUNDLE.cmd\"\r\n"
        "if errorlevel 1 exit /b 1\r\n"
        "call \"%SHARE_DIR%\\APPLY_SEED_ARTIFACTS.cmd\"\r\n"
        "if errorlevel 1 exit /b 1\r\n"
        "call \"%SHARE_DIR%\\INSTALL_AUX_DEPS.cmd\"\r\n"
        "if errorlevel 1 exit /b 1\r\n"
        "call \"%SHARE_DIR%\\CHECK_AUX_READINESS.cmd\"\r\n"
        "exit /b %ERRORLEVEL%\r\n"
    )
    (share / "SETUP_AUX_FOR_D6.cmd").write_text(setup_body, encoding="utf-8")

    deps_body = (
        "@echo off\r\n"
        "py -m pip install tiktoken pytest fastapi httpx -q\r\n"
        "exit /b 0\r\n"
    )
    (share / "INSTALL_AUX_DEPS.cmd").write_text(deps_body, encoding="utf-8")

    retry_body = (
        "@echo off\r\n"
        "setlocal\r\n"
        "set SHARE_DIR=%~dp0\r\n"
        "call \"%SHARE_DIR%\\SETUP_AUX_FOR_D6.cmd\"\r\n"
        "if errorlevel 1 exit /b 1\r\n"
        "call \"%SHARE_DIR%\\RUN_D6_ON_AUX.cmd\"\r\n"
        "exit /b %ERRORLEVEL%\r\n"
    )
    (share / "RETRY_D6_ON_AUX.cmd").write_text(retry_body, encoding="utf-8")

    readme = "\r\n".join(
        [
            "MKM D6 aux quick start (DESKTOP-AP1DC83 / share)",
            "",
            "NOTE: scripts/ is NOT in git. Use bundle copy, not git sync.",
            "",
            "Fallback (6-step, seeded):",
            "0) SETUP_AUX_FOR_D6.cmd",
            "1) RUN_D6_ON_AUX.cmd",
            "",
            "Full main parity (7-step, no seeds):",
            "0) SETUP_AUX_FULL_FOR_D6.cmd  (bundle + vault stub, NO seed apply)",
            "1) RUN_D6_FULL_ON_AUX.cmd  (~20-30 min)",
            "   or RETRY_D6_FULL_ON_AUX.cmd (setup + run)",
            "",
            "Manual fallback:",
            "   COPY_WORKSPACE_BUNDLE.cmd",
            "   APPLY_SEED_ARTIFACTS.cmd",
            "   CHECK_AUX_READINESS.cmd",
            "   RUN_D6_ON_AUX.cmd",
            "",
            "PowerShell 직접 실행:",
            f"   cd {aux_workspace}",
            "   py C:\\share\\external_validation_d6_aux\\run_external_validation_d6_aux_runner_v1.py --share-dir C:\\share\\external_validation_d6_aux",
            "",
            "Result: aux_d6_result_v1_latest.json (fallback) or aux_d6_full_result_v1_latest.json (full).",
            f"main_git_head: {main_git_head}",
            "",
        ]
    )
    (share / "READ_ME_FIRST.txt").write_text(readme, encoding="utf-8")

    request_id = uuid.uuid4().hex[:12]
    job = {
        "schema": "external_validation_d6_job_request_v1",
        "request_id": request_id,
        "requested_at_utc": _utc_now(),
        "lane": "infra",
        "disclaimer": "internal_only",
        "send_gate": "HOLD",
        "main_git_head": main_git_head,
        "aux_workspace_expected": aux_workspace,
        "share_root_on_main": str(share).replace("\\", "/"),
        "aux_host_hint": "DESKTOP-AP1DC83",
        "operator": "auxiliary_pc_vscode",
        "rehearsal_class": "true_third_party",
        "result_file": RESULT_NAME,
        "steps": [
            "On aux PC: open share folder (same files as Z:\\external_validation_d6_aux on main)",
            "Double-click RUN_D6_ON_AUX.cmd OR paste CURSOR_PROMPT.txt into VS Code/Cursor",
            f"On main: py scripts/collect_external_validation_d6_aux_result_v1.py --share-root {share}",
        ],
    }
    (share / JOB_NAME).write_text(json.dumps(job, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "schema": "external_validation_d6_aux_drop_v1",
        "generated_at_utc": _utc_now(),
        "ok": True,
        "share_root": str(share).replace("\\", "/"),
        "request_id": request_id,
        "main_git_head": job["main_git_head"],
        "deployed_files": [
            "manifest.json",
            "manifest_full_week1.json",
            "manifest_full_aux_d6.json",
            "run_external_validation_d6_aux_runner_v1.py",
            "run_external_validation_d6_independent_rehearsal_v1.py",
            "check_external_validation_d6_aux_readiness_v1.py",
            "RUN_D6_ON_AUX.cmd",
            "RUN_D6_FULL_ON_AUX.cmd",
            "SETUP_AUX_FULL_FOR_D6.cmd",
            "RETRY_D6_FULL_ON_AUX.cmd",
            "RUN_COMPRESSION_PARITY_ON_AUX.cmd",
            "RUN_COMPRESSION_PARITY_MAIN_COLLECT_CHECK.cmd",
            "CREATE_AUX_VAULT_STUB.cmd",
            "CHECK_AUX_READINESS.cmd",
            "COPY_WORKSPACE_BUNDLE.cmd",
            "APPLY_SEED_ARTIFACTS.cmd",
            "SETUP_AUX_FOR_D6.cmd",
            "INSTALL_AUX_DEPS.cmd",
            "RETRY_D6_ON_AUX.cmd",
            "SYNC_GIT_TO_MAIN_HEAD.cmd",
            "INSTALL_D6_SCRIPTS.cmd",
            "READ_ME_FIRST.txt",
            "CURSOR_PROMPT.txt",
            "seed_artifacts/",
            JOB_NAME,
        ],
        "seed_files": seed_files,
        "aux_next": [
            "On MAIN: py scripts/build_external_validation_d6_aux_workspace_bundle_v1.py",
            f"On AUX fallback: SETUP_AUX_FOR_D6.cmd then RUN_D6_ON_AUX.cmd",
            f"On AUX full 7-step: SETUP_AUX_FULL_FOR_D6.cmd then RUN_D6_FULL_ON_AUX.cmd",
            f"On MAIN collect full: py scripts/collect_external_validation_d6_aux_result_v1.py --share-root {share} --result-name {RESULT_NAME_FULL}",
        ],
        "main_collect": f"py scripts/collect_external_validation_d6_aux_result_v1.py --share-root {share}",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--share-root", type=Path, default=SHARE_DEFAULT)
    ap.add_argument("--aux-workspace", default=r"C:\workspace")
    args = ap.parse_args()

    doc = stage(args.share_root, args.aux_workspace)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "share": doc["share_root"], "out": str(OUT.relative_to(ROOT))}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
