#!/usr/bin/env python3
"""[HYPO] Compare P2 CRC stub vs salience latent PoC on Golden-40."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_latent_poc_vs_stub_v1_latest.json"
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(script: str, extra: list[str]) -> int:
    cmd = [sys.executable, str(ROOT / script), *extra]
    return subprocess.run(cmd, cwd=str(ROOT)).returncode


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--skip-run", action="store_true", help="Only compare existing artifacts")
    ap.add_argument(
        "--extended-poc-sweep",
        action="store_true",
        help="Pass --extended-sweep to PoC runner",
    )
    args = ap.parse_args()

    stub_out = (
        ROOT
        / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_latent_stub_shadow_v1_latest.json"
    )
    poc_out = (
        ROOT
        / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_latent_poc_v1_latest.json"
    )

    if not args.skip_run:
        if _run(
            "scripts/run_nextgen_latent_indexer_stub_ng40_shadow_v1.py",
            ["--out-json", str(stub_out)],
        ):
            return 1
        poc_args = ["--out-json", str(poc_out)]
        if args.extended_poc_sweep:
            poc_args.append("--extended-sweep")
        if _run("scripts/run_nextgen_latent_indexer_poc_ng40_v1.py", poc_args):
            return 1

    stub = _load(stub_out)
    poc = _load(poc_out)
    if not stub or not poc:
        print("error: missing stub or poc output", file=sys.stderr)
        return 1

    sa = stub.get("aggregate") or {}
    pa = poc.get("aggregate") or {}
    delta = {
        "saving_pp": round(
            (
                float(pa.get("global_token_saving_rate") or 0)
                - float(sa.get("global_token_saving_rate") or 0)
            )
            * 100,
            2,
        ),
        "jaccard_pp": round(
            (
                float(pa.get("avg_reconstruction_fidelity_jaccard") or 0)
                - float(sa.get("avg_reconstruction_fidelity_jaccard") or 0)
            )
            * 100,
            2,
        ),
    }

    doc = {
        "schema": "nextgen_latent_poc_vs_stub_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "stub_pointer": str(stub_out.relative_to(ROOT)).replace("\\", "/"),
        "poc_pointer": str(poc_out.relative_to(ROOT)).replace("\\", "/"),
        "stub": {
            "aggregate": sa,
            "beat_check": stub.get("beat_check"),
            "phase": stub.get("implementation_phase"),
        },
        "poc": {
            "aggregate": pa,
            "beat_check": poc.get("beat_check"),
            "phase": poc.get("implementation_phase"),
            "selected_keep_ratio": poc.get("selected_keep_ratio"),
        },
        "poc_minus_stub": delta,
        "winner": (
            "poc"
            if (poc.get("beat_check") or {}).get("beat_frozen")
            and not (stub.get("beat_check") or {}).get("beat_frozen")
            else (
                "stub"
                if (stub.get("beat_check") or {}).get("beat_frozen")
                and not (poc.get("beat_check") or {}).get("beat_frozen")
                else "neither_beat_frozen"
            )
        ),
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(args.out_json), "winner": doc["winner"], "delta": delta}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
