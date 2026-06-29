#!/usr/bin/env python3
"""Full web_ops_regime chain: CDP probe (live→portal fallback) → baselines → gate → check."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.web_ops_regime_classifier_v1 import is_auth_wall_observation

CDP = ROOT / "scripts/run_web_ops_regime_cdp_probe_v1.py"
SYNC = ROOT / "scripts/sync_web_ops_regime_pointer_baselines_v1.py"
CHECK = ROOT / "scripts/check_web_ops_regime_gate_v1.py"
DEFAULT_NEBIUS = ROOT / "reports/nvidia_nebius_console_setup_latest.json"
DEFAULT_CDP_OUT = ROOT / "reports/web_ops_regime_cdp_probe_v1_latest.json"
DEFAULT_GATE = ROOT / "reports/web_ops_regime_gate_v1_latest.json"
DEFAULT_BASELINES = ROOT / "reports/web_ops_regime_pointer_baselines_v1.json"
DEFAULT_LIVE_OBS = ROOT / "reports/web_ops_regime_live_observation_v1_latest.json"
DEFAULT_IDE_OBS = ROOT / "reports/web_ops_regime_ide_browser_observation_v1_latest.json"


def _observation_usable(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return False
    return not is_auth_wall_observation(doc)


def _live_observation_paths() -> list[Path]:
    paths: list[Path] = []
    for path in (DEFAULT_LIVE_OBS, DEFAULT_IDE_OBS):
        if _observation_usable(path) and path not in paths:
            paths.append(path)
    return paths


def _run(cmd: list[str]) -> int:
    return subprocess.run(cmd, cwd=str(ROOT)).returncode


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cdp-url", default="http://127.0.0.1:9222")
    ap.add_argument("--host-filter", default="console.nebius.com")
    ap.add_argument("--from-nebius-json", type=Path, default=DEFAULT_NEBIUS)
    ap.add_argument("--skip-live-cdp", action="store_true")
    ap.add_argument("--seed-baselines", action="store_true", default=True)
    ap.add_argument("--no-seed-baselines", dest="seed_baselines", action="store_false")
    ap.add_argument("--require-gate-pass", action="store_true", default=True)
    ap.add_argument("--require-dual-alignment", action="store_true", default=False)
    ap.add_argument("--fail-on-pointer-drift", action="store_true", default=False)
    ap.add_argument("--skip-azure", action="store_true")
    args = ap.parse_args()

    summary: dict[str, object] = {"bundle": "web_ops_regime_full_v1", "steps": []}
    py = sys.executable

    cdp_cmd = [
        py,
        str(CDP),
        "--out",
        str(DEFAULT_CDP_OUT),
        "--gate-out",
        str(DEFAULT_GATE),
        "--baselines-json",
        str(DEFAULT_BASELINES),
    ]
    if args.skip_azure:
        cdp_cmd.append("--skip-azure")

    attempts: list[tuple[str, list[str]]] = []
    if not args.skip_live_cdp:
        attempts.append(
            (
                "cdp_live",
                cdp_cmd + ["--cdp-url", args.cdp_url, "--host-filter", args.host_filter],
            )
        )
    for live_obs in _live_observation_paths():
        attempts.append(("live_observation", cdp_cmd + ["--dry-run-from-json", str(live_obs)]))
    attempts.append(
        ("portal_json_derived", cdp_cmd + ["--from-nebius-json", str(args.from_nebius_json)])
    )

    rc = 2
    mode = "none"
    winning_cmd: list[str] = []
    for mode_name, cmd in attempts:
        rc = _run(cmd)
        if rc == 0:
            mode = mode_name
            winning_cmd = cmd
            break
    summary["steps"].append({"cdp_probe": rc, "mode": mode})
    if rc != 0:
        print(json.dumps({**summary, "ok": False}, ensure_ascii=False))
        return rc

    if args.seed_baselines:
        sync_cmd = [
            py,
            str(SYNC),
            "--gate-json",
            str(DEFAULT_GATE),
            "--cdp-json",
            str(DEFAULT_CDP_OUT),
            "--out",
            str(DEFAULT_BASELINES),
            "--seed",
        ]
        rc_sync = _run(sync_cmd)
        summary["steps"].append({"sync_baselines": rc_sync})
        if rc_sync != 0:
            print(json.dumps({**summary, "ok": False}, ensure_ascii=False))
            return rc_sync

        rc_reprobe = _run(winning_cmd)
        summary["steps"].append({"cdp_reprobe_after_seed": rc_reprobe})
        if rc_reprobe != 0:
            print(json.dumps({**summary, "ok": False}, ensure_ascii=False))
            return rc_reprobe

    check_cmd = [py, str(CHECK), "--in-json", str(DEFAULT_GATE)]
    if args.require_gate_pass:
        check_cmd.append("--require-gate-pass")
    if args.require_dual_alignment:
        check_cmd.append("--require-dual-alignment")
    if args.fail_on_pointer_drift:
        check_cmd.append("--fail-on-pointer-drift")
    rc_check = _run(check_cmd)
    summary["steps"].append({"check_gate": rc_check})

    summary_py = ROOT / "scripts/build_web_ops_regime_health_summary_v1.py"
    if summary_py.is_file():
        rc_summary = _run([py, str(summary_py)])
        summary["steps"].append({"health_summary": rc_summary})

    gate_doc = json.loads(DEFAULT_GATE.read_text(encoding="utf-8-sig"))
    summary.update(
        {
            "ok": rc_check == 0,
            "gate_pass": gate_doc.get("gate_pass"),
            "worst_final_action": (gate_doc.get("conflict_resolver") or {}).get("worst_final_action"),
            "probe_count": (gate_doc.get("conflict_resolver") or {}).get("probe_count"),
            "paths": {
                "cdp_probe": str(DEFAULT_CDP_OUT),
                "gate": str(DEFAULT_GATE),
                "baselines": str(DEFAULT_BASELINES),
            },
        }
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return rc_check


if __name__ == "__main__":
    raise SystemExit(main())
