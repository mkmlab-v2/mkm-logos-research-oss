#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DROPZONE = ROOT / "reports" / "news_repro" / "latest"
OUT_JSON = ART / "external_validation_scorecard_latest.json"
OUT_MD = ART / "external_validation_scorecard_latest.md"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    for enc in ("utf-8", "utf-8-sig"):
        try:
            return json.loads(path.read_text(encoding=enc))
        except Exception:
            continue
    return None


def _check_float(value: Any, low: float, high: float) -> bool:
    try:
        val = float(value)
    except Exception:
        return False
    return low <= val <= high


def main() -> int:
    leaderboard = _read_json(ART / "btrack_compression_leaderboard_latest.json") or {}
    readiness = _read_json(ART / "news_benchmark_readiness_latest.json") or {}
    repro_bundle = _read_json(ART / "news_third_party_repro_bundle_latest.json") or {}
    digest = _read_json(DROPZONE / "independent_result_digest.json") or {}
    manifest = _read_json(DROPZONE / "external_runner_manifest.json") or {}

    best = leaderboard.get("best_overall") or {}
    checks = {
        "internal_metric_saving_plausible": _check_float(best.get("saving"), 0.40, 0.70),
        "internal_metric_integrity_locked": float(best.get("integrity", 0.0) or 0.0) >= 1.0,
        "internal_metric_jaccard_plausible": _check_float(best.get("jaccard"), 0.80, 0.98),
        "repro_bundle_attached": bool(repro_bundle.get("third_party_repro_evidence_present", False)),
        "repro_bundle_no_placeholder": not bool(repro_bundle.get("placeholder_detected", True)),
        "readiness_status_not_marketing_only": str((readiness.get("summary") or {}).get("status", "")) in {
            "READY_FOR_NEWS_CLAIMS",
            "READY_PENDING_THIRD_PARTY_REPRO",
            "NOT_READY_FOR_NEWS_CLAIMS",
        },
        "manifest_contains_environment": bool(manifest.get("environment")) or bool(manifest.get("platform")),
        "digest_contains_failure_metrics": (
            digest.get("failure_rate") is not None
            or digest.get("error_rate") is not None
            or digest.get("failed_cases") is not None
        ),
        "digest_contains_latency_metrics": (
            digest.get("latency_ms_p95") is not None
            or digest.get("p95_latency_ms") is not None
            or digest.get("latency_summary") is not None
        ),
    }

    # Strict external-ready gate: require non-marketing observability fields too.
    strict_ready = (
        checks["internal_metric_saving_plausible"]
        and checks["internal_metric_integrity_locked"]
        and checks["internal_metric_jaccard_plausible"]
        and checks["repro_bundle_attached"]
        and checks["repro_bundle_no_placeholder"]
        and checks["readiness_status_not_marketing_only"]
        and checks["manifest_contains_environment"]
        and checks["digest_contains_failure_metrics"]
        and checks["digest_contains_latency_metrics"]
    )

    blockers: list[str] = []
    if not checks["digest_contains_failure_metrics"]:
        blockers.append("Missing failure-rate style metric in `independent_result_digest.json`.")
    if not checks["digest_contains_latency_metrics"]:
        blockers.append("Missing latency metric (p95 or equivalent) in `independent_result_digest.json`.")
    if not checks["manifest_contains_environment"]:
        blockers.append("Missing runtime environment details in `external_runner_manifest.json`.")
    if not checks["repro_bundle_no_placeholder"]:
        blockers.append("Repro bundle still indicates placeholder/simulated evidence.")

    payload = {
        "schema": "external_validation_scorecard_v1",
        "generated_at_utc": _utc_now(),
        "decision": "GO_EXTERNAL_BENCHMARK_CLAIMS" if strict_ready else "HOLD_EXTERNAL_BENCHMARK_CLAIMS",
        "strict_ready": strict_ready,
        "checks": checks,
        "blockers": blockers,
        "evidence": {
            "leaderboard": "docs/final/artifacts/btrack_compression_leaderboard_latest.json",
            "readiness": "docs/final/artifacts/news_benchmark_readiness_latest.json",
            "repro_bundle": "docs/final/artifacts/news_third_party_repro_bundle_latest.json",
            "dropzone_manifest": "reports/news_repro/latest/external_runner_manifest.json",
            "dropzone_digest": "reports/news_repro/latest/independent_result_digest.json",
        },
        "required_for_go": [
            "At least one independent manifest with environment metadata.",
            "Digest must contain both failure and latency metrics.",
            "Repro bundle must be non-placeholder and attached.",
        ],
    }

    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# External Validation Scorecard (Latest)",
        "",
        f"- generated_at_utc: `{payload['generated_at_utc']}`",
        f"- decision: `{payload['decision']}`",
        f"- strict_ready: `{payload['strict_ready']}`",
        "",
        "## Blockers",
    ]
    if blockers:
        lines.extend(f"- {item}" for item in blockers)
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Gate Rule",
            "- External claims stay HOLD until manifest + digest include environment, latency, and failure metrics.",
            "",
        ]
    )
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(str(OUT_JSON))
    print(str(OUT_MD))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
