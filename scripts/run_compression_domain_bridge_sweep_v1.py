#!/usr/bin/env python3
"""B-track: compare selective gematria bridge by domain vs baseline (RQ-016)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "run_ultra_compression_default.py"
KPI_SCRIPT = ROOT / "scripts" / "report_ultra_compression_kpi_summary.py"
OUT_DEFAULT = ROOT / "docs" / "final" / "artifacts" / "compression_domain_bridge_sweep_v1_latest.json"
SCM_CASES = frozenset({"cmp2_015", "cmp2_023", "cmp2_028"})
HEALTH_CASE = "cmp2_014"


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _case_metrics(report: dict[str, Any], case_ids: frozenset[str]) -> dict[str, Any]:
    cases = (report.get("compression_metrics") or {}).get("cases") or []
    rows = [c for c in cases if str(c.get("id", "")) in case_ids]
    if not rows:
        return {"case_count": 0}
    n = len(rows)
    return {
        "case_count": n,
        "avg_jaccard": sum(float(r.get("reconstruction_fidelity_jaccard") or 0) for r in rows) / n,
        "min_jaccard": min(float(r.get("reconstruction_fidelity_jaccard") or 0) for r in rows),
        "by_id": {
            str(r.get("id")): {
                "jaccard": r.get("reconstruction_fidelity_jaccard"),
                "token_saving_rate": r.get("token_saving_rate"),
            }
            for r in rows
        },
    }


def _global_metrics(report: dict[str, Any]) -> dict[str, Any]:
    m = report.get("compression_metrics") or {}
    return {
        "global_token_saving_rate": m.get("global_token_saving_rate"),
        "avg_reconstruction_fidelity_jaccard": m.get("avg_reconstruction_fidelity_jaccard"),
        "ultra_saving_policy_min": 0.47,
        "ultra_saving_policy_ok": (
            float(m.get("global_token_saving_rate") or 0) >= 0.47
            if m.get("global_token_saving_rate") is not None
            else None
        ),
    }


def _run_variant(
    *,
    label: str,
    out_report: Path,
    bridge_domains: str,
    apply_bridge: bool,
) -> int:
    cmd = [sys.executable, str(RUNNER), "--mode", "universal", "--out", str(out_report)]
    if bridge_domains:
        cmd.extend(["--selective-bridge-policy-domains", bridge_domains])
    if apply_bridge:
        cmd.append("--apply-gematria-4d-bridge-policy")
    r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr or r.stdout, file=sys.stderr)
    return r.returncode


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--work-dir", type=Path, default=ROOT / "reports" / "constitution" / "btrack_pilot" / "_bridge_sweep")
    args = ap.parse_args()

    args.work_dir.mkdir(parents=True, exist_ok=True)
    variants = [
        ("baseline", "", False),
        ("scm_bridge", "scm", True),
        ("health_bridge", "health", True),
        ("scm_health_bridge", "scm,health", True),
    ]

    results: list[dict[str, Any]] = []
    for label, domains, apply_bridge in variants:
        out_report = args.work_dir / f"active_report_{label}.json"
        code = _run_variant(
            label=label,
            out_report=out_report,
            bridge_domains=domains,
            apply_bridge=apply_bridge,
        )
        if code != 0:
            return code
        rep = _read_json(out_report)
        results.append(
            {
                "id": label,
                "bridge_domains": domains or None,
                "apply_gematria_4d_bridge_policy": apply_bridge,
                "report_path": str(out_report.relative_to(ROOT)).replace("\\", "/"),
                "global": _global_metrics(rep),
                "scm_cases": _case_metrics(rep, SCM_CASES),
                "health_case": _case_metrics(rep, frozenset({HEALTH_CASE})).get("by_id", {}).get(HEALTH_CASE),
            }
        )

    baseline = next(r for r in results if r["id"] == "baseline")
    scm_bridge = next(r for r in results if r["id"] == "scm_bridge")
    recommendation = (
        "scm_selective_bridge_improves_scm_without_global_floor_breach"
        if (
            scm_bridge["global"].get("ultra_saving_policy_ok")
            and (scm_bridge["scm_cases"].get("min_jaccard") or 0)
            > (baseline["scm_cases"].get("min_jaccard") or 0)
        )
        else "keep_baseline_or_tune_domains"
    )

    doc = {
        "schema": "compression_domain_bridge_sweep_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "track_wall": "b_track_research_only",
        "rq": "RQ-016",
        "policy_floor": 0.47,
        "variants": results,
        "recommendation": recommendation,
        "note": "Does not mutate production ACTIVE_REPORT; restores baseline at end.",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")

    restore = subprocess.run(
        [sys.executable, str(RUNNER), "--mode", "universal"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    if restore.returncode == 0:
        subprocess.run([sys.executable, str(KPI_SCRIPT)], cwd=str(ROOT), check=False)

    print(json.dumps({"out": str(args.out), "recommendation": recommendation}, ensure_ascii=False))
    return 0 if restore.returncode == 0 else restore.returncode


if __name__ == "__main__":
    raise SystemExit(main())
