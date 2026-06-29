#!/usr/bin/env python3
"""Refresh lens sovereignty report only when SSOT inputs changed (batch, no 30y WF recompute).

Default for evolution spine step 1: fingerprint disk SSOT mtimes; skip rebuild if unchanged.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE = ROOT / "docs/final/artifacts/lens_sovereignty_ssot_refresh_state_v1.json"
DEFAULT_REPORT = ROOT / "docs/final/artifacts/lens_sovereignty_report_v1_2_latest.json"
DEFAULT_BLUEPRINT = ROOT / "docs/final/artifacts/lens_sovereignty_blueprint_v1_2.json"


def _ssot_input_paths(root: Path) -> tuple[Path, ...]:
    return (
        root / "docs/final/artifacts/emotion_weight_memory_weekly_report_latest.json",
        root
        / "projects/bitcoin-trading/memory/v2/emotion/operational_multisource_sentiment_daily_latest.jsonl",
        root / "docs/final/artifacts/myeongni_weather_fusion_profile_latest.json",
        root / "docs/final/artifacts/myeongni_promotion_gate_latest.json",
        root / "docs/final/artifacts/general_prophecy_brier_eval_latest.json",
        root / "docs/final/artifacts/logos_chronology_era_blind_eval_text_blind_v1_latest.json",
        root / "reports/biblical_history_holdout_brier_dual_report_latest.json",
        root / "reports/kospi_lens_ablation_backtest_walkforward_latest.json",
        root / "docs/final/artifacts/three_lens_horizon_empirical_eval_v2_latest.json",
    )


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _input_fingerprint(root: Path) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    for p in _ssot_input_paths(root):
        if p.is_file():
            st = p.stat()
            files.append({"path": str(p.resolve()), "mtime_ns": st.st_mtime_ns, "size": st.st_size})
        else:
            files.append({"path": str(p.resolve()), "missing": True})
    join_hits = sorted(
        root.glob("reports/btrack_session_panel_wide_prophecy_weather_*.join.meta.json"),
        key=lambda x: x.stat().st_mtime,
        reverse=True,
    )
    if join_hits:
        st = join_hits[0].stat()
        files.append(
            {
                "path": str(join_hits[0].resolve()),
                "mtime_ns": st.st_mtime_ns,
                "size": st.st_size,
                "kind": "latest_session_weather_join",
            }
        )
    return {"schema": "lens_sovereignty_ssot_fingerprint_v1", "files": files}


def _fingerprint_equal(a: dict[str, Any], b: dict[str, Any]) -> bool:
    return a.get("files") == b.get("files")


def _run_refresh(*, root: Path) -> dict[str, Any]:
    py = sys.executable
    steps: list[dict[str, Any]] = []
    for rel in (
        "scripts/build_lens_sovereignty_supplementary_rails_v1_2.py",
        "scripts/build_lens_sovereignty_report_v1.py",
    ):
        script = root / rel
        extra: list[str] = []
        if script.name.startswith("build_lens_sovereignty_report"):
            extra = ["--blueprint", str(DEFAULT_BLUEPRINT.relative_to(root)).replace("\\", "/")]
        cmd = [py, str(script)] + extra
        cp = subprocess.run(cmd, cwd=str(root), capture_output=True, text=True)
        steps.append(
            {
                "script": rel,
                "exit_code": cp.returncode,
                "stdout_tail": (cp.stdout or "")[-2000:],
                "stderr_tail": (cp.stderr or "")[-2000:],
            }
        )
        if cp.returncode != 0:
            return {"ok": False, "steps": steps}
    return {"ok": True, "steps": steps}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspace-root", type=Path, default=ROOT)
    ap.add_argument("--state", type=Path, default=DEFAULT_STATE)
    ap.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--force", action="store_true", help="Rebuild even when SSOT fingerprint unchanged.")
    ap.add_argument("--out-json", type=Path, default=None)
    ns = ap.parse_args()
    root = ns.workspace_root.resolve()
    state_path = ns.state if ns.state.is_absolute() else root / ns.state
    report_path = ns.report if ns.report.is_absolute() else root / ns.report
    out_path = ns.out_json or (root / "docs/final/artifacts/lens_sovereignty_ssot_refresh_latest.json")

    fp = _input_fingerprint(root)
    prev = {}
    if state_path.is_file():
        try:
            prev = json.loads(state_path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            prev = {}

    prev_fp = prev.get("last_fingerprint") if isinstance(prev.get("last_fingerprint"), dict) else {}
    unchanged = _fingerprint_equal(fp, prev_fp) and report_path.is_file()
    skipped = bool(unchanged and not ns.force)

    result: dict[str, Any] = {
        "schema": "lens_sovereignty_ssot_refresh_v1",
        "generated_at_utc": _utc_now(),
        "skipped": skipped,
        "skip_reason": "ssot_fingerprint_unchanged" if skipped else None,
        "forced": bool(ns.force),
        "fingerprint": fp,
        "report_path": str(report_path),
    }

    if skipped:
        result["ok"] = True
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"SKIP unchanged SSOT fingerprint -> {report_path}")
        return 0

    refresh = _run_refresh(root=root)
    result["refresh"] = refresh
    result["ok"] = bool(refresh.get("ok"))
    if not result["ok"]:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return 3

    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(
            {
                "schema": "lens_sovereignty_ssot_refresh_state_v1",
                "updated_at_utc": _utc_now(),
                "last_fingerprint": fp,
                "last_report_path": str(report_path),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"REFRESH ok -> {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
