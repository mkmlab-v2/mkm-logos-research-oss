#!/usr/bin/env python3
"""Kaggle Benchmarks local CLI spike [HYPO] research_only.

Installs/checks write-kaggle-benchmarks skill + kaggle-benchmarks SDK, validates
hello-world and optional PROMPT_DRYRUN lens micro-benchmark draft locally.

Output: reports/kaggle_benchmarks_spike_v1_latest.json
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
DEFAULT_OUT = ROOT / "reports/kaggle_benchmarks_spike_v1_latest.json"
WORKSPACE = ROOT / "reports/kaggle_benchmarks_spike_v1_workspace"
SKILL_DIR = ROOT / ".cursor/skills/write-kaggle-benchmarks"
VENDOR_SKILLS = ROOT / ".vendor/kaggle-skills/write-kaggle-benchmarks"
VENDOR_KBENCH = ROOT / ".vendor/kaggle-benchmarks"
SWEEP_EVIDENCE = ROOT / "reports/prompt_dryrun_local_mkm_lens_sweep_v1_latest.json"
PROMPT_CARD = ROOT / "reports/nemotron_lora_mkm_lens_prompt_card_v1_latest.json"

HELLO_TASK = WORKSPACE / "hello_world_task.py"
LENS_TASK = WORKSPACE / "mkm_lens_tag_compliance_micro_v1.py"
EXAMPLE_TASK = WORKSPACE / "example_task.py"
ENV_FILE = WORKSPACE / ".env"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str], *, cwd: Path | None = None, env: dict | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd or ROOT),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=600,
    )


def _load_env_file(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        out[key.strip()] = val.strip()
    return out


def _merge_env(base: dict[str, str | None], extra: dict[str, str]) -> dict[str, str | None]:
    merged = dict(os.environ)
    merged.update(base)
    merged.update(extra)
    return merged


def _ensure_skill() -> dict:
    ok = SKILL_DIR.is_dir() and (SKILL_DIR / "SKILL.md").is_file()
    if not ok and VENDOR_SKILLS.is_dir():
        SKILL_DIR.mkdir(parents=True, exist_ok=True)
        for name in ("SKILL.md", "README.md"):
            src = VENDOR_SKILLS / name
            if src.is_file():
                (SKILL_DIR / name).write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        ok = (SKILL_DIR / "SKILL.md").is_file()
    return {
        "skill_path": str(SKILL_DIR),
        "installed": ok,
        "vendor_clone": str(VENDOR_SKILLS),
    }


def _check_kbench_import() -> dict:
    cp = _run([sys.executable, "-c", "import kaggle_benchmarks as k; print(getattr(k,'__version__','unknown'))"])
    return {
        "ok": cp.returncode == 0,
        "version": (cp.stdout or "").strip() if cp.returncode == 0 else None,
        "stderr_tail": (cp.stderr or "")[-300:] if cp.returncode != 0 else "",
    }


def _check_kaggle_cli() -> dict:
    cp = _run(["kaggle", "--version"])
    cp2 = _run(["kaggle", "benchmarks", "--help"])
    return {
        "ok": cp.returncode == 0 and cp2.returncode == 0,
        "version": (cp.stdout or cp.stderr or "").strip(),
        "benchmarks_subcommand": cp2.returncode == 0,
    }


def _ensure_init(skip_init: bool) -> dict:
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    if ENV_FILE.is_file() and skip_init:
        return {"ran": False, "skipped": True, "env_file": str(ENV_FILE)}
    cp = _run(
        [
            "kaggle",
            "benchmarks",
            "init",
            "-y",
            "--env-file",
            str(ENV_FILE),
            "--example-file",
            str(EXAMPLE_TASK),
        ],
        cwd=WORKSPACE,
    )
    return {
        "ran": True,
        "exit_code": cp.returncode,
        "ok": cp.returncode == 0,
        "stdout_tail": (cp.stdout or "")[-800:],
        "stderr_tail": (cp.stderr or "")[-400:],
        "env_file": str(ENV_FILE),
    }


def _validate_task(task_path: Path, label: str) -> dict:
    env = _merge_env({}, _load_env_file(ENV_FILE))
    cp = _run([sys.executable, str(task_path)], cwd=WORKSPACE, env=env)
    run_files = sorted(WORKSPACE.glob("*.run.json"))
    return {
        "label": label,
        "task_path": str(task_path.relative_to(ROOT)).replace("\\", "/"),
        "exit_code": cp.returncode,
        "ok": cp.returncode == 0,
        "run_json_count": len(run_files),
        "run_json_files": [p.name for p in run_files[-5:]],
        "stdout_tail": (cp.stdout or "")[-1200:],
        "stderr_tail": (cp.stderr or "")[-600:] if cp.returncode != 0 else "",
    }


def _optional_push_run(task_slug: str, task_file: Path, model: str, do_remote: bool) -> dict:
    if not do_remote:
        return {"skipped": True, "reason": "remote push/run not requested"}
    env = _merge_env({}, _load_env_file(ENV_FILE))
    push = _run(
        ["kaggle", "benchmarks", "tasks", "push", task_slug, "-f", str(task_file.name), "--wait"],
        cwd=WORKSPACE,
        env=env,
    )
    run = _run(
        ["kaggle", "benchmarks", "tasks", "run", task_slug, "-m", model, "--wait"],
        cwd=WORKSPACE,
        env=env,
    )
    status = _run(["kaggle", "benchmarks", "tasks", "status", task_slug], cwd=WORKSPACE, env=env)
    return {
        "push_exit_code": push.returncode,
        "run_exit_code": run.returncode,
        "status_exit_code": status.returncode,
        "ok": push.returncode == 0 and run.returncode == 0,
        "push_stdout_tail": (push.stdout or "")[-600:],
        "run_stdout_tail": (run.stdout or "")[-400:],
        "status_stdout_tail": (status.stdout or "")[-800:],
    }


def _refresh_auth() -> dict:
    cp = _run(["kaggle", "benchmarks", "auth", "-y"], cwd=WORKSPACE)
    env = _load_env_file(ENV_FILE)
    return {
        "exit_code": cp.returncode,
        "ok": cp.returncode == 0,
        "expiry": env.get("MODEL_PROXY_EXPIRY_TIME"),
        "stdout_tail": (cp.stdout or "")[-400:],
        "stderr_tail": (cp.stderr or "")[-300:] if cp.returncode != 0 else "",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Kaggle Benchmarks local CLI spike v1 [HYPO]")
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--skip-init", action="store_true", help="Skip kaggle b init if .env exists")
    ap.add_argument("--skip-lens", action="store_true", help="Skip lens micro-benchmark validate")
    ap.add_argument(
        "--remote-hello",
        action="store_true",
        help="Also push/run hello task on Kaggle (uses model proxy quota)",
    )
    ap.add_argument(
        "--remote-lens",
        action="store_true",
        help="Also push/run lens micro-benchmark on Kaggle (uses model proxy quota)",
    )
    ap.add_argument(
        "--remote",
        action="store_true",
        help="Shorthand: --remote-hello --remote-lens",
    )
    ap.add_argument(
        "--refresh-auth",
        action="store_true",
        help="Run kaggle benchmarks auth -y before validate/remote",
    )
    ap.add_argument("--remote-model", default="gemini-3-flash-preview")
    ap.add_argument("--strict", action="store_true", help="exit 1 unless core hello validate passes")
    args = ap.parse_args()
    if args.remote:
        args.remote_hello = True
        args.remote_lens = True

    doc: dict = {
        "schema": "kaggle_benchmarks_spike_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "wired_into_train": False,
        "auto_apply": False,
        "track_wall": "no_track_a_live_auto_merge",
        "evidence_paths": {
            "prompt_dryrun_sweep": str(SWEEP_EVIDENCE.relative_to(ROOT)).replace("\\", "/"),
            "nemotron_prompt_card": str(PROMPT_CARD.relative_to(ROOT)).replace("\\", "/"),
        },
        "steps": {},
    }

    doc["steps"]["skill_install"] = _ensure_skill()
    doc["steps"]["kbench_import"] = _check_kbench_import()
    doc["steps"]["kaggle_cli"] = _check_kaggle_cli()
    doc["steps"]["benchmarks_init"] = _ensure_init(skip_init=args.skip_init and not args.refresh_auth)
    if args.refresh_auth:
        doc["steps"]["benchmarks_auth_refresh"] = _refresh_auth()

    hello = _validate_task(HELLO_TASK, "hello_world_local_validate")
    doc["steps"]["hello_world"] = {
        "build": {"task_file": str(HELLO_TASK.relative_to(ROOT)).replace("\\", "/"), "built": HELLO_TASK.is_file()},
        "validate_run": hello,
    }

    if args.remote_hello:
        doc["steps"]["hello_world"]["remote"] = _optional_push_run(
            "mkm-hello-world-math",
            HELLO_TASK,
            args.remote_model,
            True,
        )

    # Also record prior example_task spike if present
    if EXAMPLE_TASK.is_file():
        doc["steps"]["example_what_is_kaggle"] = {
            "task_file": str(EXAMPLE_TASK.relative_to(ROOT)).replace("\\", "/"),
            "note": "from kaggle b init scaffold; validated separately in this workspace session",
        }

    lens_block: dict = {
        "packaged": LENS_TASK.is_file(),
        "manifest": str((WORKSPACE / "mkm_lens_tag_compliance_micro_v1.manifest.json").relative_to(ROOT)).replace(
            "\\", "/"
        ),
        "wired_into_train": False,
        "profile_count": 4,
        "skipped": args.skip_lens,
    }
    if not args.skip_lens and LENS_TASK.is_file():
        lens_block["validate_run"] = _validate_task(LENS_TASK, "lens_micro_local_validate")
    if args.remote_lens and LENS_TASK.is_file():
        lens_block["remote"] = _optional_push_run(
            "mkm-lens-tag-compliance-micro-v1",
            LENS_TASK,
            args.remote_model,
            True,
        )
    doc["steps"]["lens_micro_benchmark_draft"] = lens_block

    core_ok = (
        doc["steps"]["skill_install"].get("installed")
        and doc["steps"]["kbench_import"].get("ok")
        and doc["steps"]["kaggle_cli"].get("ok")
        and (
            doc["steps"]["benchmarks_init"].get("ok")
            or doc["steps"]["benchmarks_init"].get("skipped")
        )
        and hello.get("ok")
    )
    lens_ok = args.skip_lens or lens_block.get("validate_run", {}).get("ok", False)
    doc["summary"] = {
        "core_ok": core_ok,
        "lens_ok": lens_ok,
        "all_requested_ok": core_ok and lens_ok,
        "verdict_ko": (
            "Kaggle Benchmarks CLI spike OK — hello-world validate pass"
            + ("; lens 4-profile draft validate pass" if lens_ok and not args.skip_lens else "")
            + " [HYPO research_only · Track A/실매매 합선 없음]"
            if core_ok
            else "Kaggle Benchmarks CLI spike partial/fail — see steps.*.exit_code"
        ),
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": core_ok, "out": str(args.out_json), "core_ok": core_ok, "lens_ok": lens_ok}, ensure_ascii=False))

    if args.strict and not core_ok:
        return 1
    return 0 if core_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
