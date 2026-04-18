# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.85, L:0.84, K:0.57, M:0.67}
# Balance: 90
# Purpose: Detect drift in codebook/codepack/report fingerprints and reference integrity.
# Keywords: codebook, codepack, drift, integrity, gate
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path("C:/workspace")
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_CODEPACK = ART / "defense_code_pack_v1.json"
DEFAULT_REPORT = ART / "lg_washer_integrity_validation_report_v1_latest.json"
DEFAULT_EXEC_PACK = ART / "challenge_ax_vertical_lg_hs_execution_pack_v1.json"
DEFAULT_OUT = ART / "codebook_codepack_drift_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _exists_rel(rel: str) -> bool:
    return (ROOT / rel).exists()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--codepack", type=Path, default=DEFAULT_CODEPACK)
    ap.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--execution-pack", type=Path, default=DEFAULT_EXEC_PACK)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--strict", action="store_true", help="Exit non-zero when drift_status != STABLE")
    args = ap.parse_args()

    codepack = _load_json(args.codepack)
    report = _load_json(args.report)
    execution_pack = _load_json(args.execution_pack)

    fp = {
        "defense_code_pack_sha256": _sha(args.codepack),
        "lg_report_sha256": _sha(args.report),
        "execution_pack_sha256": _sha(args.execution_pack),
        "codepack_version": codepack.get("version"),
        "codepack_status": codepack.get("status"),
        "report_status": report.get("status"),
        "report_codebook_version": ((report.get("codebook_profile") or {}).get("version")),
    }

    expected = {
        "defense_code_pack_sha256": "87772d94001bbb3420d8f4931cef58f371f68330948adad2aae50ab263c46982",
        # Baseline fingerprint for docs/final/artifacts/lg_washer_integrity_validation_report_v1_latest.json
        # (report_ready_local_baseline). Update when the report artifact is intentionally regenerated.
        "lg_report_sha256": "0e0625be92fec3200441539357a1a9daf74bed55075d82eb6121b20214fdeaac",
    }

    drift_items: list[str] = []
    if fp["defense_code_pack_sha256"] != expected["defense_code_pack_sha256"]:
        drift_items.append("defense_code_pack_changed")
    if fp["lg_report_sha256"] != expected["lg_report_sha256"]:
        drift_items.append("lg_report_latest_changed")

    missing_refs: list[str] = []
    for rel in (
        "docs/final/artifacts/lg_washer_voice_dataset_strategy_recommended_v1.json",
        "docs/final/artifacts/lg_washer_voice_golden_split_manifest_v1.json",
        "docs/final/artifacts/defense_edge_execution_evidence_v1.json",
    ):
        if not _exists_rel(rel):
            missing_refs.append(rel)

    ep_refs = execution_pack.get("repo_evidence_paths") or []
    if "docs/final/artifacts/lg_washer_voice_dataset_strategy_recommended_v1.json" not in ep_refs:
        drift_items.append("execution_pack_missing_strategy_ref")

    drift_status = "STABLE" if (not drift_items and not missing_refs) else "DRIFT"

    out_doc = {
        "schema": "codebook_codepack_drift_v1",
        "generated_at_utc": _utc_now(),
        "drift_status": drift_status,
        "drift_items": drift_items,
        "missing_references": missing_refs,
        "fingerprints": fp,
        "expected_baseline": expected,
        "recommendation_ko": "DRIFT면 codepack/report 재빌드 후 제출 문안 수치 동기화",
    }

    args.out.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(args.out))
    print(drift_status)

    if args.strict and drift_status != "STABLE":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
