from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


def _recent_files(path: Path, days: int) -> list[Path]:
    if not path.exists():
        return []
    cut = _now() - timedelta(days=days)
    out: list[Path] = []
    for p in path.rglob("*"):
        if not p.is_file():
            continue
        mtime = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
        if mtime >= cut:
            out.append(p)
    return out


def build() -> int:
    root = Path("C:/workspace")
    art = root / "docs" / "final" / "artifacts"
    reports = root / "reports"
    art.mkdir(parents=True, exist_ok=True)

    keep_refs = [
        "docs/final/CENTRAL_AGENT_MEMORY_V1.md",
        "docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md",
        "scripts/run_fact_lock_bundle.ps1",
    ]

    hold_recent = [
        str(p.relative_to(root)).replace("\\", "/")
        for p in _recent_files(art, 7)
        if ("draft" in p.name.lower() or "btrack" in p.name.lower())
    ]

    prune_candidates = [
        str(p.relative_to(root)).replace("\\", "/")
        for p in _recent_files(reports, 30)
        if ("latest" in p.name.lower() and p.suffix.lower() in {".json", ".md"})
    ]

    payload: dict[str, Any] = {
        "schema": "memory_pruning_routing_status_v1",
        "generated_at_utc": _iso(_now()),
        "policy": {
            "keep": "verified ssot/code paths and reproducible automation scripts",
            "hold": "btrack/draft artifacts for bounded observation",
            "prune": "stale latest pointers/log derivatives not referenced by active chains",
        },
        "routing": {
            "keep_refs": keep_refs,
            "hold_recent_artifacts_7d": hold_recent[:100],
            "prune_candidates_latest_reports_30d": prune_candidates[:200],
        },
        "counts": {
            "keep_ref_count": len(keep_refs),
            "hold_count": len(hold_recent),
            "prune_candidate_count": len(prune_candidates),
        },
        "next_actions": [
            "Retain keep_refs as SSOT anchors.",
            "Review hold artifacts weekly; promote only with reproducible script evidence.",
            "Prune candidates in batches after 24h safety observation.",
        ],
    }

    out_json = art / "memory_pruning_routing_status_latest.json"
    out_md = art / "memory_pruning_routing_status_latest.md"
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    out_md.write_text(
        "\n".join(
            [
                "# Memory Pruning Routing Status",
                "",
                f"- generated_at_utc: `{payload['generated_at_utc']}`",
                f"- keep_ref_count: `{payload['counts']['keep_ref_count']}`",
                f"- hold_count: `{payload['counts']['hold_count']}`",
                f"- prune_candidate_count: `{payload['counts']['prune_candidate_count']}`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"wrote: {out_json}")
    print(f"wrote: {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(build())

