#!/usr/bin/env python3
"""Logos Track D — dual-backend ST eval, distill enrich, digest, external gates."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
ART = ROOT / "docs/final/artifacts"
THEMES = ("dan_aramaic", "john_1_logos")
OUT_DEFAULT = ROOT / "reports/logos_track_b_phase_d_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(name: str, cmd: list[str], *, ok_codes: set[int] | None = None) -> dict[str, Any]:
    t0 = time.perf_counter()
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    codes = ok_codes or {0}
    return {
        "name": name,
        "exit_code": proc.returncode,
        "elapsed_sec": round(time.perf_counter() - t0, 2),
        "stdout_tail": (proc.stdout or "")[-400:],
        "stderr_tail": (proc.stderr or "")[-200:],
        "ok": proc.returncode in codes,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []

    for tid in THEMES:
        steps.append(
            _run(
                f"st_index_{tid}",
                [PY, "scripts/build_logos_themed_vector_index_v1.py", "--theme", tid, "--try-sentence-transformers"],
            )
        )
        steps.append(
            _run(
                f"st_query_{tid}",
                [PY, "scripts/query_logos_themed_vector_index_v1.py", "--theme", tid, "--top-k", "5"],
            )
        )
        steps.append(
            _run(
                f"distill_enrich_{tid}",
                [PY, "scripts/enrich_logos_distill_themed_vector_v1.py", "--theme", tid, "--in-place"],
            )
        )

    steps.append(_run("retrieval_eval", [PY, "scripts/build_logos_themed_retrieval_eval_v1.py"]))
    steps.append(_run("dual_backend_eval", [PY, "scripts/build_logos_themed_retrieval_dual_backend_eval_v1.py"]))
    steps.append(_run("dual_digest", [PY, "scripts/build_logos_commander_dual_theme_digest_v1.py"]))
    steps.append(
        _run(
            "delegate_chain",
            [
                PY,
                "scripts/run_logos_track_b_delegate_chain_v1.py",
                "--try-ollama-distill",
                "--reuse-ollama-smoke",
            ],
        )
    )
    steps.append(
        _run("external_validation", [PY, "scripts/run_external_validation_recommended_sequence_v1.py", "--skip-p2"])
    )

    dual_path = ROOT / "reports/logos_themed_retrieval_dual_backend_v1_latest.json"
    dual_themes: list[dict[str, Any]] = []
    if dual_path.is_file():
        try:
            dual_themes = json.loads(dual_path.read_text(encoding="utf-8-sig")).get("themes") or []
        except json.JSONDecodeError:
            pass

    ext_path = ROOT / "reports/external_validation_recommended_sequence_v1_latest.json"
    ext_p1: dict[str, Any] = {}
    if ext_path.is_file():
        try:
            ext_p1 = json.loads(ext_path.read_text(encoding="utf-8-sig")).get("phases", {}).get("P1_infra_prep") or {}
        except json.JSONDecodeError:
            pass

    core_ok = all(
        s.get("ok")
        for s in steps
        if s.get("name") not in ("delegate_chain",)
    )

    summary = {
        "schema": "logos_track_b_phase_d_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "dual_backend_eval": dual_themes,
        "external_validation": {
            "readiness_all_ok": ext_p1.get("readiness_all_ok"),
            "send_gate": json.loads(ext_path.read_text(encoding="utf-8-sig")).get("gates", {}).get("send_gate")
            if ext_path.is_file()
            else None,
        },
        "artifacts": {
            "dual_backend": "reports/logos_themed_retrieval_dual_backend_v1_latest.json",
            "dual_digest": "reports/logos_track_b_commander_dual_theme_digest_latest.md",
            "phase_d": "reports/logos_track_b_phase_d_v1_latest.json",
        },
        "steps": steps,
        "core_ok": core_ok,
        "reproduce": "py scripts/run_logos_track_b_phase_d_v1.py",
    }

    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": core_ok, "out": str(out_path.relative_to(ROOT))}, ensure_ascii=False))
    return 0 if core_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
