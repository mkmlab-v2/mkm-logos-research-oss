from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build consolidated MKM AI final ops bundle."
    )
    parser.add_argument("--workspace-root", default="C:/workspace")
    return parser.parse_args()


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def _find_sync_marker(root: Path) -> Path | None:
    candidates = [
        Path("G:/공유 드라이브/MKM_DATA_VAULT/vault/notebooklm_sources/_LAST_SYNC.txt"),
        Path("G:/MKM_DATA_VAULT/vault/notebooklm_sources/_LAST_SYNC.txt"),
        root / "vault" / "notebooklm_sources" / "_LAST_SYNC.txt",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def _parse_sync_marker(path: Path | None) -> Dict[str, Any]:
    if path is None or not path.exists():
        return {"exists": False}
    raw = path.read_text(encoding="utf-8", errors="replace")
    lines = [x.strip() for x in raw.splitlines() if x.strip()]
    data: Dict[str, Any] = {"exists": True, "path": str(path)}
    for line in lines:
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        key = k.strip().lower().replace(" ", "_")
        data[key] = v.strip()
    return data


def main() -> int:
    args = _parse_args()
    root = Path(args.workspace_root)
    artifacts = root / "docs" / "final" / "artifacts"

    pointer = _read_json(artifacts / "mkm_ai_status_pointer_latest.json")
    decision = _read_json(artifacts / "mkm_ai_v2_promotion_decision_latest.json")
    weekly = _read_json(artifacts / "mkm_ai_v2_weekly_readiness_report_latest.json")
    readiness = _read_json(artifacts / "mkm_ai_v2_readiness_latest.json")
    sync_marker = _parse_sync_marker(_find_sync_marker(root))

    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    bundle = {
        "schema": "mkm_ai_final_ops_bundle_v1",
        "generated_at_utc": now,
        "status": pointer.get("status"),
        "system_label": pointer.get("system_label"),
        "is_final": pointer.get("is_final"),
        "promotion_decision": decision.get("decision"),
        "promotion_ready": decision.get("promotion_ready"),
        "weekly_pass_rate_percent": weekly.get("pass_rate_percent"),
        "weekly_sample_count": weekly.get("sample_count"),
        "readiness_overall_passed": readiness.get("overall_passed"),
        "notebooklm_sync_marker": sync_marker,
        "evidence": {
            "status_pointer": "docs/final/artifacts/mkm_ai_status_pointer_latest.json",
            "promotion_decision": "docs/final/artifacts/mkm_ai_v2_promotion_decision_latest.json",
            "weekly_readiness": "docs/final/artifacts/mkm_ai_v2_weekly_readiness_report_latest.json",
            "readiness_latest": "docs/final/artifacts/mkm_ai_v2_readiness_latest.json",
        },
    }

    out_json = artifacts / "mkm_ai_final_ops_bundle_latest.json"
    out_md = artifacts / "mkm_ai_final_ops_bundle_latest.md"
    out_json.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# MKM AI Final Ops Bundle (Latest)",
        "",
        f"- generated_at_utc: `{now}`",
        f"- status: `{bundle.get('status')}`",
        f"- system_label: `{bundle.get('system_label')}`",
        f"- is_final: `{bundle.get('is_final')}`",
        f"- promotion_decision: `{bundle.get('promotion_decision')}`",
        f"- promotion_ready: `{bundle.get('promotion_ready')}`",
        f"- weekly_pass_rate_percent: `{bundle.get('weekly_pass_rate_percent')}`",
        f"- weekly_sample_count: `{bundle.get('weekly_sample_count')}`",
        f"- readiness_overall_passed: `{bundle.get('readiness_overall_passed')}`",
        "",
        "## NotebookLM Sync Marker",
        f"- exists: `{sync_marker.get('exists')}`",
        f"- path: `{sync_marker.get('path')}`",
        f"- utc: `{sync_marker.get('utc')}`",
        f"- copied_operations: `{sync_marker.get('copied_operations')}`",
        f"- skipped_(missing): `{sync_marker.get('skipped_(missing)')}`",
    ]
    out_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print(f"ops bundle written: {out_json}")
    print(f"ops brief written: {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
