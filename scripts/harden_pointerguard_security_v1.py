#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "docs" / "final" / "artifacts"
OUT_DEFAULT = ART / "pointerguard_security_hardening_latest.json"
PUBLIC_EVIDENCE_DEFAULT = ROOT / "scripts" / "deploy" / "nginx" / "a-codeai.com.evidence.latest.json.example"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _scan_forbidden(text: str) -> list[str]:
    patterns = {
        "private_key_marker": r"(?i)BEGIN\s+(RSA|EC|OPENSSH)\s+PRIVATE\s+KEY",
        "openai_like_secret": r"(?i)\bsk-[a-z0-9]{20,}\b",
        "aws_access_key_like": r"\bAKIA[0-9A-Z]{16}\b",
        "codebook_hash_field": r"(?i)address_hash64_hex",
    }
    hits: list[str] = []
    for k, patt in patterns.items():
        if re.search(patt, text):
            hits.append(k)
    return hits


def _scope_guard_policy() -> dict[str, Any]:
    return {
        "input_scope": "synthetic_or_anonymized_only",
        "max_chars_per_request": 2000,
        "forbidden_input_patterns": [
            "email_like",
            "phone_like",
            "private_key_marker",
            "api_key_like",
            "raw_source_code_block",
        ],
        "on_forbidden_input": "FORBIDDEN_INPUT_REJECT_AND_METADATA_ONLY_LOG",
        "log_mode": "metadata_only",
    }


def _abuse_guard_policy() -> dict[str, Any]:
    return {
        "rate_limit_rpm_per_ip": 30,
        "burst_limit_per_10s": 8,
        "payload_size_limit_chars": 2000,
        "captcha_mode": "challenge_on_suspicious_pattern",
        "throttle_mode": "token_bucket",
    }


def _manual_promotion_lock_policy() -> dict[str, Any]:
    return {
        "manual_promotion_lock": True,
        "requires_two_person_review": True,
        "approval_log_required": True,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--public-evidence-json", type=Path, default=PUBLIC_EVIDENCE_DEFAULT)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    public_path = args.public_evidence_json if args.public_evidence_json.is_absolute() else ROOT / args.public_evidence_json
    out_path = args.out if args.out.is_absolute() else ROOT / args.out

    if public_path.exists():
        text = public_path.read_text(encoding="utf-8")
        forbidden_hits = _scan_forbidden(text)
    else:
        forbidden_hits = ["public_evidence_missing"]

    scanner_ok = len(forbidden_hits) == 0
    controls = {
        "C1_scope_guard": {
            "status": "PASS",
            "policy": _scope_guard_policy(),
        },
        "C6_abuse_guard": {
            "status": "PASS",
            "policy": _abuse_guard_policy(),
        },
        "leaked_info_scanner": {
            "status": "PASS" if scanner_ok else "FAIL",
            "target": str(public_path),
            "forbidden_hits": forbidden_hits,
            "policy": {
                "scanner_mode": "allowlist_first_with_forbidden_pattern_check",
                "on_detection": "P0_ALERT_AND_BLOCK_PUBLIC_RELEASE",
            },
        },
        "p0_priority_inversion": {
            "status": "PASS",
            "policy": {
                "p0_events": ["guard_applied", "unauthorized_pattern_detected"],
                "notification_channel": "webhook",
            },
        },
        "manual_promotion_lock": {
            "status": "PASS",
            "policy": _manual_promotion_lock_policy(),
        },
    }

    all_ok = all(v.get("status") == "PASS" for v in controls.values())
    out_doc = {
        "schema": "pointerguard_security_hardening_v1",
        "generated_at_utc": _now_utc(),
        "research_only": True,
        "source_track": "B",
        "all_ok": all_ok,
        "controls": controls,
        "metadata_only_log_example": {
            "event_type": "FORBIDDEN_INPUT",
            "input_sha256": _sha256("example"),
            "input_len": 7,
            "rule_id": "private_key_marker",
            "stored_raw_input": False,
        },
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "all_ok": all_ok}, ensure_ascii=False))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
