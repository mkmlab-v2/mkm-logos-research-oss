#!/usr/bin/env python3
"""OSI fetch + xref ingest + router refresh [HYPO]."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
DEFAULT_OUT = ROOT / "reports/logos_osi_xref_ingest_chain_v1_latest.json"


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
    ap.add_argument("--osi-dir", type=Path, default=None)
    ap.add_argument("--use-fixture-sample", action="store_true")
    ap.add_argument("--skip-download", action="store_true")
    ap.add_argument("--ack-license-mit-pd", action="store_true")
    ap.add_argument("--max-edges", type=int, default=150000)
    ap.add_argument("--skip-pytest", action="store_true")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    use_fixture = args.use_fixture_sample or args.osi_dir is None
    steps: list[dict] = []

    if not use_fixture:
        fetch_cmd = [PY, "scripts/fetch_logos_osi_release_v1.py", "--dest", str(args.osi_dir)]
        if args.skip_download:
            fetch_cmd.append("--skip-download")
        steps.append(_run("fetch_osi", fetch_cmd))

    ingest_cmd = [PY, "scripts/ingest_logos_osi_xref_edges_v1.py", "--max-edges", str(args.max_edges)]
    if use_fixture:
        ingest_cmd.append("--use-fixture-sample")
    else:
        ingest_cmd.extend(["--osi-dir", str(args.osi_dir)])
        if not args.ack_license_mit_pd:
            raise SystemExit("real osi ingest requires --ack-license-mit-pd")
        ingest_cmd.append("--ack-license-mit-pd")

    router_cmd = [
        PY,
        "scripts/run_logos_subgraph_graphrag_router_v1.py",
        "--sinew-xref-jsonl",
        "docs/final/artifacts/logos_sinew_xref_edges_v1.jsonl",
        "--osi-xref-jsonl",
        "docs/final/artifacts/logos_osi_xref_edges_v1.jsonl",
    ]

    steps.extend(
        [
            _run("osi_xref_ingest", ingest_cmd),
            _run("subgraph_router_with_xrefs", router_cmd),
            _run("external_kg_manifest", [PY, "scripts/build_logos_external_kg_ingest_manifest_v1.py"]),
        ]
    )

    if not args.skip_pytest:
        steps.append(
            _run(
                "pytest_osi",
                [PY, "-m", "pytest", "tests/test_ingest_logos_osi_xref_edges_v1.py", "-q", "--tb=short"],
            )
        )

    all_ok = all(s["ok"] for s in steps)
    report = {
        "schema": "logos_osi_xref_ingest_chain_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "send_gate": "HOLD",
        "all_ok": all_ok,
        "steps": steps,
        "reproduce": "py scripts/run_logos_osi_xref_ingest_chain_v1.py --osi-dir storage/external_kg/osi_v1 --ack-license-mit-pd --skip-download",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": all_ok, "out": str(args.out)}, ensure_ascii=False))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
