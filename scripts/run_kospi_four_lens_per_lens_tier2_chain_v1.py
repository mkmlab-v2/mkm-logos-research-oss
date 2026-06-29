#!/usr/bin/env python3
"""Per-lens Tier2 orchestrator: Field · Logos · Myeongni · Sasang [HYPO]."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(name: str, cmd: list[str], *, timeout: int = 300) -> dict:
    cp = subprocess.run(
        cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout
    )
    return {"step": name, "exit_code": cp.returncode, "tail": ((cp.stdout or "") + (cp.stderr or "")).strip()[-500:]}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-band-wf", action="store_true")
    ap.add_argument("--skip-fusion-rebuild", action="store_true")
    ap.add_argument("--skip-premium", action="store_true")
    args = ap.parse_args()

    steps: list[dict] = []

    if not args.skip_band_wf:
        steps.append(
            _run(
                "conflict_band_coverage_wf",
                [PY, "scripts/run_kospi_four_lens_conflict_band_coverage_wf_v1.py"],
            )
        )

    steps.append(_run("field_tier2", [PY, "scripts/build_field_lens_vol_band_tier2_v1.py"]))
    steps.append(_run("myeongni_tier2", [PY, "scripts/build_myeongni_lens_tier2_v1.py"]))

    if not args.skip_fusion_rebuild:
        steps.append(_run("rebuild_fusion_base", [PY, "scripts/build_kospi_four_lens_graphrag_fusion_v1.py"]))

    steps.append(_run("logos_tier2", [PY, "scripts/build_logos_lens_conflict_digest_tier2_v1.py"]))
    steps.append(_run("sasang_tier2", [PY, "scripts/build_sasang_lens_veto_tier2_v1.py"]))
    steps.append(_run("fusion_tier2_attach", [PY, "scripts/build_kospi_four_lens_graphrag_fusion_v1.py", "--attach-tier2"]))

    if not args.skip_premium:
        steps.append(
            _run(
                "premium_multilens",
                [PY, "scripts/build_premium_btrack_multilens_report_v1.py", "--mode", "best-effort"],
                timeout=180,
            )
        )

    ok = all(s["exit_code"] == 0 for s in steps)

    summary: dict = {}
    for key, path in (
        ("field", "reports/field_lens_vol_band_tier2_v1_latest.json"),
        ("logos", "reports/logos_lens_conflict_digest_tier2_v1_latest.json"),
        ("myeongni", "reports/myeongni_lens_tier2_v1_latest.json"),
        ("sasang", "reports/sasang_lens_veto_tier2_v1_latest.json"),
    ):
        p = ROOT / path
        if p.is_file():
            try:
                summary[key] = json.loads(p.read_text(encoding="utf-8-sig"))
            except json.JSONDecodeError:
                summary[key] = None

    out = ROOT / "reports/kospi_four_lens_per_lens_tier2_chain_v1_latest.json"
    doc = {
        "schema": "kospi_four_lens_per_lens_tier2_chain_v1",
        "generated_at_utc": _utc(),
        "ok": ok,
        "hypothesis_tier": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "steps": steps,
        "summary": {
            "field_tier2_role": (summary.get("field") or {}).get("tier2_role"),
            "field_delta_band": ((summary.get("field") or {}).get("holdout_metrics") or {}).get(
                "delta_vol_widen_minus_active"
            ),
            "logos_routes": len(((summary.get("logos") or {}).get("excess_unwind_routes") or [])),
            "myeongni_paths": len(((summary.get("myeongni") or {}).get("corpus_paths") or [])),
            "sasang_force_hold": (summary.get("sasang") or {}).get("force_hold"),
        },
        "reproduce": "py scripts/run_kospi_four_lens_per_lens_tier2_chain_v1.py",
    }
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "summary": doc["summary"]}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
