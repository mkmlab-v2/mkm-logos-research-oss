#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
FIXED = ART / "trackb_quaternion_top_combo_fixed_set_latest.json"
STRESS = ART / "trackb_quaternion_top_combo_stress_grid_latest.json"
OUT_JSON = ART / "trackb_quaternion_top_combo_public_safe_profile_latest.json"
OUT_MD = ART / "trackb_quaternion_top_combo_public_safe_profile_latest.md"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    fixed = json.loads(FIXED.read_text(encoding="utf-8"))
    stress = json.loads(STRESS.read_text(encoding="utf-8"))

    stress_by_artifact = {row.get("artifact"): row for row in stress.get("rows", [])}
    kept = []
    dropped = []

    for item in fixed.get("selected", []):
        artifact = item.get("artifact")
        summary = (stress_by_artifact.get(artifact, {}).get("stress_summary") or {})
        min_exact = summary.get("min_exact_sequence_match_rate_over_grid")
        if isinstance(min_exact, (int, float)) and float(min_exact) >= 0.75:
            kept.append(item)
        else:
            dropped.append(
                {
                    "artifact": artifact,
                    "min_exact_sequence_match_rate_over_grid": min_exact,
                }
            )

    now = _utc_now()
    payload = {
        "schema": "trackb_quaternion_top_combo_public_safe_profile_v1",
        "generated_at_utc": now,
        "source_fixed_set": "docs/final/artifacts/trackb_quaternion_top_combo_fixed_set_latest.json",
        "source_stress_grid": "docs/final/artifacts/trackb_quaternion_top_combo_stress_grid_latest.json",
        "selection_rule": "Keep candidates with stress_summary.min_exact_sequence_match_rate_over_grid >= 0.75",
        "public_profile_decision": "ALLOW_ONLY_STRESS_ROBUST_CANDIDATES",
        "selected_count": len(kept),
        "selected": kept,
        "dropped_count": len(dropped),
        "dropped": dropped,
        "fact_safe_note": "Public showcase profile excludes stress-collapsing candidates; research candidates remain Track B only.",
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# TrackB Public Safe Profile (Latest)",
        "",
        f"- generated_at_utc: `{now}`",
        f"- selected_count: `{len(kept)}`",
        f"- dropped_count: `{len(dropped)}`",
        "- decision: `ALLOW_ONLY_STRESS_ROBUST_CANDIDATES`",
        "",
        "## Selected Artifacts",
    ]
    if kept:
        lines.extend(f"- `{item.get('artifact')}`" for item in kept)
    else:
        lines.append("- none")

    lines.extend(["", "## Dropped Artifacts"])
    if dropped:
        lines.extend(
            f"- `{item.get('artifact')}` (min_exact={item.get('min_exact_sequence_match_rate_over_grid')})"
            for item in dropped
        )
    else:
        lines.append("- none")

    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(str(OUT_JSON))
    print(str(OUT_MD))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
