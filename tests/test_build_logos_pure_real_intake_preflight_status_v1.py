import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_logos_pure_real_intake_preflight_status_v1.py"


def test_build_logos_pure_real_intake_preflight_status_smoke(tmp_path: Path) -> None:
    action_pack_json = tmp_path / "action_pack.json"
    news_jsonl = tmp_path / "news.jsonl"
    out_json = tmp_path / "out.json"

    action_pack_json.write_text(
        json.dumps(
            {
                "schema": "logos_pure_real_action_pack_v1",
                "status": {"today_utc": "2026-05-05"},
                "today_targets": {"recommended_total_rows_today": 3},
            }
        ),
        encoding="utf-8",
    )
    news_jsonl.write_text(
        "\n".join(
            [
                json.dumps({"is_synthetic_source": False, "as_of_utc": "2026-05-05T00:00:00Z"}),
                json.dumps({"is_synthetic_source": False, "as_of_utc": "2026-05-05T12:00:00Z"}),
                json.dumps({"is_synthetic_source": True, "as_of_utc": "2026-05-05T13:00:00Z"}),
                json.dumps({"is_synthetic_source": False, "as_of_utc": "2026-05-04T13:00:00Z"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--action-pack-json",
            str(action_pack_json),
            "--news-jsonl",
            str(news_jsonl),
            "--output-json",
            str(out_json),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(out_json.read_text(encoding="utf-8"))
    assert doc.get("schema") == "logos_pure_real_intake_preflight_status_v1"
    assert int(doc.get("actual_rows_today", 0)) == 2
    assert int(doc.get("shortage_rows_today", 0)) == 1
    assert doc.get("status") == "FAIL_NEED_MORE_ROWS"

