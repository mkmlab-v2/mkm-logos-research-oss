from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_logos_symbolic_data_hygiene_audit_v1.py"


def test_build_logos_symbolic_data_hygiene_audit_smoke(tmp_path: Path) -> None:
    news = tmp_path / "news.jsonl"
    news.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "schema_version": "news_observation_v1",
                        "observation_id": "a",
                        "as_of_utc": "2026-04-29T00:00:00Z",
                        "published_utc": "2026-04-29T00:00:00Z",
                        "source_id": "label_guided_seed",
                        "canonical_text": "x",
                    }
                ),
                json.dumps(
                    {
                        "schema_version": "news_observation_v1",
                        "observation_id": "b",
                        "as_of_utc": "2026-04-29T00:00:00Z",
                        "published_utc": "2026-04-29T00:00:00Z",
                        "source_id": "external_macro_signals",
                        "canonical_text": "y",
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    backtest = tmp_path / "bt.json"
    backtest.write_text(
        json.dumps(
            {
                "summary": {
                    "non_synthetic_n_evaluated": 1,
                    "skipped_counts": {"missing_future_label": 0},
                    "skipped_non_synthetic_counts": {"missing_future_label": 0},
                }
            }
        ),
        encoding="utf-8",
    )
    gate = tmp_path / "gate.json"
    gate.write_text(
        json.dumps(
            {
                "decision": "GO_RESEARCH_PROMOTION_CANDIDATE",
                "all_pass": True,
                "metrics_snapshot": {"non_synthetic_n_evaluated": 1},
                "checks": {"min_non_synthetic_samples_pass": True},
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "audit.json"
    prev = tmp_path / "prev.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--news-jsonl",
            str(news),
            "--backtest-json",
            str(backtest),
            "--gate-json",
            str(gate),
            "--output-json",
            str(out),
            "--previous-audit-json",
            str(prev),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stdout + cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("status") == "ok"
    assert doc.get("news_counts", {}).get("non_synthetic_rows") == 1
    assert doc.get("risk_flags", {}).get("non_synthetic_gate_check_pass") is True
    drift = doc.get("drift_comparison") or {}
    assert isinstance(drift.get("flags"), dict)
    assert drift.get("flags", {}).get("hit_rate_drop_exceeds_threshold") is False

