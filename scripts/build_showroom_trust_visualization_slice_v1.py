# Keywords: showroom, trust_visualization_v0, stt_routing_audit, thin slice
"""Emit a small JSON next to jemaai-cloud-mvp static HTML for Visualization v0 (read-only)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]


def _utc_now_z() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_dashboard(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _nodata_trust() -> Dict[str, Any]:
    return {
        "state": "NODATA",
        "path": "docs/final/schemas/trust_visualization_panel_v0.example.json",
        "role": "trust_visualization_read_only_v0",
    }


def _nodata_stt() -> Dict[str, Any]:
    return {
        "state": "NODATA",
        "summary_path": "reports/stt_routing_audit_log_v1_summary_latest.json",
        "role": "silver_stt_audit_summary_v0",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--dashboard",
        type=Path,
        default=ROOT / "docs" / "final" / "artifacts" / "mkm_trackc_ops_dashboard_latest.json",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=ROOT
        / "projects"
        / "bitcoin-trading"
        / "ops"
        / "windows-rehearsal"
        / "jemaai-cloud-mvp"
        / "showroom_trust_visualization_slice_v0.json",
    )
    args = ap.parse_args()

    dash = _read_dashboard(args.dashboard)
    tc = dash.get("trackc") if isinstance(dash.get("trackc"), dict) else {}
    trust = tc.get("trust_visualization_v0")
    stt = tc.get("stt_routing_audit_log_slice")
    if not isinstance(trust, dict):
        trust = _nodata_trust()
    if not isinstance(stt, dict):
        stt = _nodata_stt()

    try:
        rel_dash = str(args.dashboard.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        rel_dash = str(args.dashboard)

    doc: Dict[str, Any] = {
        "schema": "showroom_trust_visualization_slice_v0",
        "version": "0.1.0",
        "hypothesis_tag": "[HYPO]",
        "generated_at_utc": _utc_now_z(),
        "source_dashboard_rel": rel_dash,
        "trust_visualization_v0": trust,
        "stt_routing_audit_log_slice": stt,
        "boundary_note": "Read-only showroom slice from Track C ops dashboard; not a trading signal.",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"out": str(args.out), "trust_state": trust.get("state"), "stt_state": stt.get("state")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
