#!/usr/bin/env python3
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, pstdev
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
OUT_JSON = ART / "news_grade_plus_scorecard_latest.json"
OUT_MD = ART / "news_grade_plus_scorecard_latest.md"


@dataclass
class RunRecord:
    digest_path: str
    manifest_path: str
    runner_id: str
    saving: float | None
    jaccard: float | None
    integrity: float | None
    has_failure_metric: bool
    has_latency_metric: bool


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


def _scan_runs() -> list[RunRecord]:
    base = ROOT / "reports" / "news_repro"
    if not base.exists():
        return []

    records: list[RunRecord] = []
    for digest_path in base.rglob("independent_result_digest.json"):
        manifest_path = digest_path.with_name("external_runner_manifest.json")
        digest = _read_json(digest_path) or {}
        manifest = _read_json(manifest_path) or {}
        metrics = digest.get("metrics") or {}

        has_failure = any(k in digest for k in ("failure_rate", "error_rate", "failed_cases"))
        has_latency = any(k in digest for k in ("latency_ms_p95", "p95_latency_ms", "latency_summary"))

        records.append(
            RunRecord(
                digest_path=str(digest_path),
                manifest_path=str(manifest_path),
                runner_id=str(digest.get("runner_id") or manifest.get("runner_id") or "").strip(),
                saving=float(metrics["saving"]) if isinstance(metrics.get("saving"), (int, float)) else None,
                jaccard=float(metrics["jaccard"]) if isinstance(metrics.get("jaccard"), (int, float)) else None,
                integrity=float(metrics["integrity"]) if isinstance(metrics.get("integrity"), (int, float)) else None,
                has_failure_metric=has_failure,
                has_latency_metric=has_latency,
            )
        )
    return records


def _safe_std(values: list[float]) -> float | None:
    if not values:
        return None
    if len(values) == 1:
        return 0.0
    return float(pstdev(values))


def _std_under_threshold(values: list[float], threshold: float) -> bool:
    std = _safe_std(values)
    if std is None:
        return False
    return std <= threshold


def main() -> int:
    records = _scan_runs()
    runners = sorted({r.runner_id for r in records if r.runner_id})

    saving_values = [r.saving for r in records if r.saving is not None]
    jaccard_values = [r.jaccard for r in records if r.jaccard is not None]
    integrity_values = [r.integrity for r in records if r.integrity is not None]

    checks = {
        "minimum_total_runs_5": len(records) >= 5,
        "minimum_independent_runners_3": len(runners) >= 3,
        "all_runs_have_failure_metric": all(r.has_failure_metric for r in records) if records else False,
        "all_runs_have_latency_metric": all(r.has_latency_metric for r in records) if records else False,
        "integrity_floor_1_0_all_runs": all((r.integrity or 0.0) >= 1.0 for r in records if r.integrity is not None)
        and bool(integrity_values),
        "saving_variance_stable": _std_under_threshold(saving_values, 0.05),
        "jaccard_variance_stable": _std_under_threshold(jaccard_values, 0.05),
    }

    ready = all(checks.values())
    blockers = [name for name, ok in checks.items() if not ok]

    payload = {
        "schema": "news_grade_plus_scorecard_v1",
        "generated_at_utc": _utc_now(),
        "decision": "GO_NEWS_GRADE_PLUS" if ready else "HOLD_NEWS_GRADE_PLUS",
        "news_grade_plus_ready": ready,
        "summary": {
            "total_runs": len(records),
            "independent_runner_count": len(runners),
            "runner_ids": runners,
            "saving_mean": mean(saving_values) if saving_values else None,
            "saving_std": _safe_std(saving_values),
            "jaccard_mean": mean(jaccard_values) if jaccard_values else None,
            "jaccard_std": _safe_std(jaccard_values),
            "integrity_mean": mean(integrity_values) if integrity_values else None,
        },
        "checks": checks,
        "blockers": blockers,
        "required_for_go": [
            ">=5 independent reproducibility runs",
            ">=3 distinct runner_id values",
            "failure and latency metrics present in all digest files",
            "stable variance (std <= 0.05) on saving and jaccard across runs",
        ],
    }

    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md = [
        "# News Grade Plus Scorecard",
        "",
        f"- decision: `{payload['decision']}`",
        f"- total_runs: `{payload['summary']['total_runs']}`",
        f"- independent_runner_count: `{payload['summary']['independent_runner_count']}`",
        "",
        "## Blockers",
    ]
    if blockers:
        md.extend(f"- {b}" for b in blockers)
    else:
        md.append("- none")
    md.append("")
    OUT_MD.write_text("\n".join(md), encoding="utf-8")
    print(str(OUT_JSON))
    print(str(OUT_MD))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
