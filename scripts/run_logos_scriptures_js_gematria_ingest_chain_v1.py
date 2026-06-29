#!/usr/bin/env python3
"""scriptures-js gematria lexicon fetch + ingest + manifest refresh [HYPO]."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
DEFAULT_OUT = ROOT / "reports/logos_scriptures_js_gematria_ingest_chain_v1_latest.json"
DEFAULT_SRC = ROOT / "storage/external_kg/scriptures_js_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _run(label: str, cmd: list[str]) -> dict:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    return {
        "label": label,
        "cmd": cmd,
        "exit_code": proc.returncode,
        "ok": proc.returncode == 0,
        "tail": ((proc.stdout or "") + (proc.stderr or "")).strip()[-500:],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scriptures-js-dir", type=Path, default=DEFAULT_SRC)
    ap.add_argument("--use-fixture-sample", action="store_true")
    ap.add_argument("--skip-download", action="store_true")
    ap.add_argument("--skip-tflsj", action="store_true")
    ap.add_argument("--ack-license-verify-upstream", action="store_true")
    ap.add_argument("--max-entries", type=int, default=300000)
    ap.add_argument("--skip-pytest", action="store_true")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    use_fixture = args.use_fixture_sample
    steps: list[dict] = []

    if not use_fixture:
        fetch_cmd = [PY, "scripts/fetch_logos_scriptures_js_gematria_release_v1.py", "--dest", str(args.scriptures_js_dir)]
        if args.skip_download:
            fetch_cmd.append("--skip-download")
        if args.skip_tflsj:
            fetch_cmd.append("--skip-tflsj")
        steps.append(_run("fetch_scriptures_js", fetch_cmd))

    ingest_cmd = [PY, "scripts/ingest_logos_scriptures_js_gematria_lexicon_v1.py", "--max-entries", str(args.max_entries)]
    if use_fixture:
        ingest_cmd.append("--use-fixture-sample")
    else:
        ingest_cmd.extend(["--scriptures-js-dir", str(args.scriptures_js_dir)])
        if not args.ack_license_verify_upstream:
            raise SystemExit("real ingest requires --ack-license-verify-upstream")
        ingest_cmd.append("--ack-license-verify-upstream")
        if args.skip_tflsj:
            ingest_cmd.append("--skip-tflsj")

    steps.extend(
        [
            _run("scriptures_js_gematria_ingest", ingest_cmd),
            _run("external_kg_manifest", [PY, "scripts/build_logos_external_kg_ingest_manifest_v1.py"]),
        ]
    )

    if not args.skip_pytest:
        steps.append(
            _run(
                "pytest_scriptures_js_gematria",
                [
                    PY,
                    "-m",
                    "pytest",
                    "tests/test_ingest_logos_scriptures_js_gematria_lexicon_v1.py",
                    "-q",
                    "--tb=short",
                ],
            )
        )

    all_ok = all(s["ok"] for s in steps)
    report = {
        "schema": "logos_scriptures_js_gematria_ingest_chain_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "send_gate": "HOLD",
        "all_ok": all_ok,
        "steps": steps,
        "reproduce": (
            "py scripts/run_logos_scriptures_js_gematria_ingest_chain_v1.py "
            "--scriptures-js-dir storage/external_kg/scriptures_js_v1 "
            "--ack-license-verify-upstream --skip-download"
        ),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": all_ok, "out": str(args.out)}, ensure_ascii=False))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
