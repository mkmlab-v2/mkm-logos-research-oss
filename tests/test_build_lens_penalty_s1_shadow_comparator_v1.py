from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_build_lens_penalty_s1_shadow_comparator_v1(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    script = repo / "scripts" / "build_lens_penalty_s1_shadow_comparator_v1.py"

    weekly = tmp_path / "weekly.json"
    sweep = tmp_path / "sweep.json"
    allowlist = tmp_path / "allowlist.json"
    out = tmp_path / "comparator.json"

    weekly.write_text(
        json.dumps(
            {
                "summary": {"total_events": 20, "total_fail": 12, "strict_max_fail_rate": 0.45},
                "per_lens": [
                    {"lens_id": "myeongni", "events": 10, "fail_count": 10},
                    {"lens_id": "logos", "events": 10, "fail_count": 2},
                ],
            }
        ),
        encoding="utf-8",
    )
    sweep.write_text(
        json.dumps(
            {
                "per_lens": [
                    {
                        "lens_id": "myeongni",
                        "recommend_flip_shadow_candidate": True,
                        "flip_simulation": {"fail_count": 1},
                    },
                    {
                        "lens_id": "logos",
                        "recommend_flip_shadow_candidate": False,
                        "flip_simulation": {"fail_count": 9},
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    allowlist.write_text(
        json.dumps(
            {
                "schema": "lens_penalty_s1_shadow_allowlist_v1",
                "enabled": True,
                "allowed_flip_lenses": ["myeongni"],
            }
        ),
        encoding="utf-8",
    )

    subprocess.run(
        [
            sys.executable,
            str(script),
            "--weekly-json",
            str(weekly),
            "--sweep-json",
            str(sweep),
            "--allowlist-json",
            str(allowlist),
            "--out",
            str(out),
        ],
        check=True,
        cwd=repo,
    )

    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["schema"] == "lens_penalty_s1_shadow_comparator_v1"
    assert payload["summary"]["baseline_fail_rate"] == 0.6
    assert payload["summary"]["simulated_fail_rate"] == 0.15
    assert payload["summary"]["flip_candidates"] == 1
    assert payload["summary"]["delta_strict_gap"] < 0
