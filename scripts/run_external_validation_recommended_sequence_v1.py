#!/usr/bin/env python3
"""Run P0→P2 external validation recommended sequence (MS pack → infra prep → Ollama smoke)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
OUT_DEFAULT = ROOT / "reports/external_validation_recommended_sequence_v1_latest.json"
STUB_URL = "http://127.0.0.1:8010/health"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_step(name: str, cmd: list[str], *, cwd: Path | None = None) -> dict[str, Any]:
    t0 = time.perf_counter()
    proc = subprocess.run(cmd, cwd=cwd or ROOT, capture_output=True, text=True)
    elapsed = round(time.perf_counter() - t0, 2)
    return {
        "name": name,
        "cmd": cmd,
        "exit_code": proc.returncode,
        "elapsed_sec": elapsed,
        "stdout_tail": (proc.stdout or "")[-800:],
        "stderr_tail": (proc.stderr or "")[-400:],
        "ok": proc.returncode == 0,
    }


def _http_ok(url: str, timeout: float = 3.0) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return 200 <= resp.status < 300
    except (urllib.error.URLError, TimeoutError, ValueError):
        return False


def _local_stub_smoke() -> dict[str, Any]:
    started_proc: subprocess.Popen[str] | None = None
    if not _http_ok(STUB_URL):
        started_proc = subprocess.Popen(
            [
                PY,
                "-m",
                "uvicorn",
                "scripts.compression_token_api_stub:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8010",
            ],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        for _ in range(20):
            if _http_ok(STUB_URL):
                break
            time.sleep(0.5)
    health_ok = _http_ok(STUB_URL)
    result: dict[str, Any] = {
        "name": "local_compression_stub_8010",
        "health_url": STUB_URL,
        "health_ok": health_ok,
        "started_stub": started_proc is not None,
        "ok": health_ok,
        "human_gate": "VPS nginx binding remains Tier 3 — not covered here",
    }
    if started_proc is not None and started_proc.poll() is None:
        started_proc.terminate()
        try:
            started_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            started_proc.kill()
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--skip-p2", action="store_true", help="Skip Ollama / btrack backend smoke")
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []

    # P0 — MS / evidence packs
    for name, script in [
        ("P0_week2_closure", "scripts/build_external_validation_week2_closure_v1.py"),
        ("P0_minimal_pack", "scripts/build_external_validation_minimal_pack_v1.py"),
        ("P0_ms_evidence_pack", "scripts/build_external_validation_ms_evidence_pack_v1.py"),
    ]:
        steps.append(_run_step(name, [PY, script]))

    # P1 — infra prep (local automatable; nginx deploy = human)
    for name, script in [
        ("P1_bench_landing_payload", "scripts/build_a_codeai_public_bench_landing_payload_v1.py"),
        ("P1_public_binding_check", "scripts/check_a_codeai_public_binding_v1.py"),
        ("P1_open_bench_binding_check", "scripts/check_a_codeai_open_bench_binding_v1.py"),
        ("P1_launch_checklist", "scripts/build_a_codeai_public_benchmark_launch_checklist_v1.py"),
    ]:
        steps.append(_run_step(name, [PY, script]))
    steps.append(_local_stub_smoke())

    # P2 — Ollama mainline + B-track backend smoke
    if not args.skip_p2:
        steps.append(_run_step("P2_ollama_local_smoke", [PY, "scripts/ollama_local_smoke_v1.py"]))
        steps.append(
            _run_step(
                "P2_btrack_backend_smoke_ollama",
                [PY, "scripts/run_btrack_agent_backend_smoke_v1.py", "--backends", "ollama"],
            )
        )

    p0_ok = all(s.get("ok") for s in steps if str(s.get("name", "")).startswith("P0_"))
    p1_scripts_ok = all(
        s.get("ok")
        for s in steps
        if str(s.get("name", "")).startswith("P1_") and s.get("name") != "P1_open_bench_binding_check"
    )
    open_bench = next((s for s in steps if s.get("name") == "P1_open_bench_binding_check"), {})
    stub = next((s for s in steps if s.get("name") == "local_compression_stub_8010"), {})
    p2_ok = all(s.get("ok") for s in steps if str(s.get("name", "")).startswith("P2_"))

    signoff_path = ROOT / "docs/final/artifacts/compression_b2b_legal_send_signoff_v1_latest.json"
    signoff = {}
    if signoff_path.is_file():
        signoff = json.loads(signoff_path.read_text(encoding="utf-8-sig"))

    launch_path = ROOT / "docs/final/artifacts/a_codeai_public_benchmark_launch_checklist_v1.json"
    launch = {}
    if launch_path.is_file():
        launch = json.loads(launch_path.read_text(encoding="utf-8-sig"))

    open_bench_art = ROOT / "docs/final/artifacts/a_codeai_open_bench_binding_check_latest.json"
    open_bench_doc = {}
    if open_bench_art.is_file():
        open_bench_doc = json.loads(open_bench_art.read_text(encoding="utf-8-sig"))

    summary = {
        "schema": "external_validation_recommended_sequence_v1",
        "generated_at_utc": _utc_now(),
        "phases": {
            "P0_ms_proposal": {
                "ok": p0_ok,
                "paste": "reports/external_validation_ms_evidence_pack_v1_latest/ms_proposal_headline_links_v1.txt",
                "one_pager_ko": "reports/external_validation_ms_evidence_pack_v1_latest/ms_proposal_one_pager_ko_v1.txt",
            },
            "P1_infra_prep": {
                "scripts_ok": p1_scripts_ok,
                "local_stub_8010_ok": bool(stub.get("health_ok")),
                "open_bench_binding_all_ok": bool(open_bench_doc.get("all_ok")),
                "readiness_all_ok": bool(launch.get("summary", {}).get("readiness_all_ok")),
                "human_next": "VPS: bash scripts/deploy/linux/deploy_a_codeai_landing_from_repo.sh",
            },
            "P2_ollama_btrack": {"ok": p2_ok if not args.skip_p2 else None, "skipped": args.skip_p2},
        },
        "gates": {
            "send_gate": signoff.get("send_gate"),
            "ready_for_external_send": signoff.get("ready_for_external_send"),
        },
        "steps": steps,
        "reproduce": "py scripts/run_external_validation_recommended_sequence_v1.py",
    }

    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    all_script_ok = all(s.get("ok") for s in steps if "exit_code" in s)
    print(
        json.dumps(
            {
                "ok": all_script_ok,
                "out": str(out_path.relative_to(ROOT)),
                "P0": p0_ok,
                "P1_local_stub": stub.get("health_ok"),
                "P1_open_bench_live": open_bench_doc.get("all_ok"),
                "P2": p2_ok if not args.skip_p2 else "skipped",
            },
            ensure_ascii=False,
        )
    )
    return 0 if p0_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
