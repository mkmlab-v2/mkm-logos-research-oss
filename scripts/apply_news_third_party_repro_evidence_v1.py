#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_BUNDLE = ART / "news_third_party_repro_bundle_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    for enc in ("utf-8", "utf-8-sig"):
        try:
            return json.loads(path.read_text(encoding=enc))
        except Exception:
            continue
    return {}


def _contains_placeholder(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False
    markers = [
        "PLACEHOLDER_TEMPLATE_ONLY",
        "REPLACE_WITH_REAL_",
        "placeholder template",
        "SIMULATED_INTERNAL_NOT_THIRD_PARTY",
    ]
    t = text.lower()
    return any(m.lower() in t for m in markers)


def main() -> int:
    ap = argparse.ArgumentParser(description="Apply third-party reproducibility evidence into news bundle.")
    ap.add_argument("--bundle-json", default=str(DEFAULT_BUNDLE))
    ap.add_argument("--manifest-json", required=True, help="External runner manifest JSON path")
    ap.add_argument("--raw-log", required=True, help="Raw benchmark log file path")
    ap.add_argument("--result-digest-json", required=True, help="Independent result digest JSON path")
    ap.add_argument("--signed-statement", required=True, help="Signed reproducibility statement path")
    ap.add_argument("--runner-id", required=True, help="Third-party runner identifier")
    ap.add_argument("--signer", required=True, help="Signer name or org")
    args = ap.parse_args()

    bundle_path = Path(args.bundle_json) if Path(args.bundle_json).is_absolute() else (ROOT / args.bundle_json)
    manifest = Path(args.manifest_json) if Path(args.manifest_json).is_absolute() else (ROOT / args.manifest_json)
    raw_log = Path(args.raw_log) if Path(args.raw_log).is_absolute() else (ROOT / args.raw_log)
    digest = Path(args.result_digest_json) if Path(args.result_digest_json).is_absolute() else (ROOT / args.result_digest_json)
    signed = Path(args.signed_statement) if Path(args.signed_statement).is_absolute() else (ROOT / args.signed_statement)

    required = [manifest, raw_log, digest, signed]
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        raise SystemExit("Missing required evidence files:\n- " + "\n- ".join(missing))

    bundle = _read_json(bundle_path)
    if not bundle:
        bundle = {
            "schema": "news_third_party_repro_bundle_v1",
            "generated_at_utc": _utc_now(),
            "status": "PENDING_EXTERNAL_EXECUTION",
            "third_party_repro_evidence_present": False,
            "required_artifacts": [],
            "runbook": [],
        }

    placeholder_detected = any(_contains_placeholder(p) for p in required)
    bundle["generated_at_utc"] = _utc_now()
    bundle["status"] = (
        "TEMPLATE_EVIDENCE_ATTACHED_INVALID"
        if placeholder_detected
        else "EVIDENCE_ATTACHED_AWAITING_REVIEW"
    )
    bundle["third_party_repro_evidence_present"] = not placeholder_detected
    bundle["placeholder_detected"] = placeholder_detected
    bundle["evidence"] = {
        "runner_id": args.runner_id,
        "signer": args.signer,
        "attached_at_utc": _utc_now(),
        "files": {
            "external_runner_manifest": {
                "path": str(manifest.resolve()),
                "sha256": _sha256(manifest),
            },
            "raw_logs_with_checksums": {
                "path": str(raw_log.resolve()),
                "sha256": _sha256(raw_log),
            },
            "independent_result_digest": {
                "path": str(digest.resolve()),
                "sha256": _sha256(digest),
            },
            "signed_repro_statement": {
                "path": str(signed.resolve()),
                "sha256": _sha256(signed),
            },
        },
    }
    if placeholder_detected:
        bundle["validation_note"] = (
            "Template/placeholders detected in attached files. Replace with real third-party outputs."
        )
    else:
        bundle["validation_note"] = "No placeholder markers detected in attached files."

    bundle_path.parent.mkdir(parents=True, exist_ok=True)
    bundle_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(bundle_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

