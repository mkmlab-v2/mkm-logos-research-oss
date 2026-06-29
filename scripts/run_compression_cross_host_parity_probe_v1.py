#!/usr/bin/env python3
"""Locked compression probe for main vs aux cross-host parity (raw metrics)."""
from __future__ import annotations

import argparse
import json
import os
import platform
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable

PROBE_TENANT = "cross-host-parity-v1"
PROBE_INPUT_JSONL = "data/compression/stateless_poc_open_structured_v1.jsonl"
PROBE_MAX_CASES = 10
POC_OUT = ROOT / f"reports/customer_compression_stateless_poc_{PROBE_TENANT}_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/compression_cross_host_parity_probe_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _child_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONOPTIMIZE"] = "0"
    return env


def _env_fingerprint() -> dict[str, Any]:
    codebook_path: str | None = None
    codebook_exists = False
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    try:
        from scripts.core.master_codebook_lexicon_v1_bridge import resolve_latest_codebook_path

        resolved = resolve_latest_codebook_path()
        if resolved is not None:
            codebook_path = str(resolved).replace("\\", "/")
            codebook_exists = resolved.is_file()
    except Exception as exc:  # noqa: BLE001 — diagnostic only
        codebook_path = f"resolve_error:{type(exc).__name__}"
    return {
        "python_version": platform.python_version(),
        "python_optimize": os.environ.get("PYTHONOPTIMIZE"),
        "platform": platform.platform(),
        "codebook_path": codebook_path,
        "codebook_exists": codebook_exists,
    }


def _metrics_from_poc(doc: dict[str, Any]) -> dict[str, Any]:
    agg = doc.get("aggregate") or {}
    raw_saving = agg.get("mean_token_saving_rate_proxy")
    raw_jaccard = agg.get("mean_jaccard_proxy")
    rows = doc.get("case_count")
    repair = raw_saving
    return {
        "raw": {
            "mean_token_saving_rate_proxy": raw_saving,
            "mean_jaccard_proxy": raw_jaccard,
            "parse_ok_rate": 1.0 if doc.get("parse_or_api_failures", 0) == 0 else None,
            "alignment_pass_rate": (doc.get("cases_passed", 0) / rows) if rows else None,
            "rows": rows,
        },
        "repair_v2": {
            "mean_token_saving_rate_proxy": repair,
            "mean_jaccard_proxy": raw_jaccard,
            "repair_applied_count": 0,
            "rows": rows,
            "note": "stateless_packet harness — no repair processor",
        },
        "delta": {
            "alignment_pass_rate_delta_repair_v2_minus_raw": 0.0,
            "mean_token_saving_rate_proxy_delta_repair_v2_minus_raw": 0.0,
            "mean_jaccard_proxy_delta_repair_v2_minus_raw": 0.0,
        },
    }


def run_probe(*, host_label: str, out_path: Path) -> dict[str, Any]:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts.run_compression_pilot_roi_chain_v1 import _resolve_input_corpus

    corpus = _resolve_input_corpus(
        PROBE_TENANT,
        input_jsonl=Path(PROBE_INPUT_JSONL),
        sandbox_mode=False,
        max_cases=PROBE_MAX_CASES,
    )
    cmd = [
        PY,
        "scripts/run_customer_compression_stateless_poc_v1.py",
        "--input-jsonl",
        corpus.relative_to(ROOT).as_posix(),
        "--max-cases",
        str(PROBE_MAX_CASES),
        "--out-json",
        POC_OUT.relative_to(ROOT).as_posix(),
    ]
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        capture_output=True,
        text=True,
        env=_child_env(),
        check=False,
    )
    poc_doc: dict[str, Any] = {}
    if POC_OUT.is_file():
        poc_doc = json.loads(POC_OUT.read_text(encoding="utf-8-sig"))

    metrics = _metrics_from_poc(poc_doc) if poc_doc else {}
    report = {
        "schema": "compression_cross_host_parity_probe_v1",
        "generated_at_utc": _utc(),
        "host_label": host_label,
        "hostname": socket.gethostname(),
        "workspace_root": str(ROOT),
        "probe": {
            "tenant_id": PROBE_TENANT,
            "input_jsonl": PROBE_INPUT_JSONL,
            "max_cases": PROBE_MAX_CASES,
            "skip_metering": True,
            "relax_pass_gate": False,
            "sandbox_mode": False,
        },
        "pilot_exit_code": proc.returncode,
        "poc_exit_code": proc.returncode,
        "poc_mode": "direct_stateless_poc_v1",
        "poc_report_path": str(POC_OUT.relative_to(ROOT)).replace("\\", "/") if POC_OUT.is_file() else None,
        "env_fingerprint": _env_fingerprint(),
        "metrics": metrics,
        "chain_ok": proc.returncode == 0 and bool(poc_doc),
        "status": "ok" if proc.returncode == 0 and poc_doc else "fail",
        "log_tail": ((proc.stdout or "") + (proc.stderr or "")).strip()[-600:],
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--host-label", default="main", help="main | aux")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    doc = run_probe(host_label=args.host_label, out_path=args.out)
    print(json.dumps({"ok": doc["status"] == "ok", "out": str(args.out), "status": doc["status"]}))
    return 0 if doc["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
