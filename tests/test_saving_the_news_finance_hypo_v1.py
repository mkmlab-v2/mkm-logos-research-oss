from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/news_observation_v1_finance_hypo.sample.jsonl"
BENCH_SCRIPT = ROOT / "scripts/run_saving_the_news_news_rt_bench_v1.py"
STATUS_SCRIPT = ROOT / "scripts/build_saving_the_news_finance_hypo_status_v1.py"
INGEST_SCRIPT = ROOT / "scripts/build_news_observation_from_external_feed_v1.py"


def test_finance_hypo_bench_does_not_sync_main_contract(tmp_path: Path) -> None:
    cohort = tmp_path / "finance.jsonl"
    cohort.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    bench_out = tmp_path / "bench_finance.json"
    contract_before = (ROOT / "docs/final/artifacts/saving_the_news_news_rt_bench_contract_v1_latest.json").read_text(
        encoding="utf-8"
    )

    cp = subprocess.run(
        [
            sys.executable,
            str(BENCH_SCRIPT),
            "--cohort-jsonl",
            str(cohort),
            "--min-rows",
            "10",
            "--output-json",
            str(bench_out),
            "--no-sync-contract",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stdout + cp.stderr
    doc = json.loads(bench_out.read_text(encoding="utf-8"))
    assert doc["measurement_status"] == "COMPLETE"
    assert doc["cohort_id"] == "finance"
    assert doc["observation_row_count"] == 10
    contract_after = (ROOT / "docs/final/artifacts/saving_the_news_news_rt_bench_contract_v1_latest.json").read_text(
        encoding="utf-8"
    )
    assert contract_before == contract_after


def test_finance_hypo_status_go_no_go(tmp_path: Path) -> None:
    bench = {
        "measurement_status": "COMPLETE",
        "observation_row_count": 10,
        "kpi": {"jaccard_fidelity_proxy": 0.52, "token_saving_ratio": 0.38, "integrity_score": 1.0},
    }
    bench_path = tmp_path / "bench.json"
    bench_path.write_text(json.dumps(bench), encoding="utf-8")
    out = tmp_path / "status.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(STATUS_SCRIPT),
            "--bench-json",
            str(bench_path),
            "--output-json",
            str(out),
            "--jaccard-go-floor",
            "0.50",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stdout + cp.stderr
    status = json.loads(out.read_text(encoding="utf-8"))
    assert status["second_axis_go"] is True
    assert status["promote_to_deck"] is False
    assert status["go_no_go"]["verdict"] == "GO_SECOND_AXIS_PILOT"


def test_standalone_ingest_no_merge(tmp_path: Path) -> None:
    feed = tmp_path / "feed.json"
    feed.write_text(
        json.dumps(
            {
                "schema": "external_feed_drop_v1",
                "generated_at_utc": "2026-05-25T08:00:00Z",
                "source": {"provider": "bbc_business"},
                "data": [
                    {
                        "id": "a1",
                        "title": "Finance headline one",
                        "url": "https://example.com/1",
                        "published_utc": "2026-05-25T08:00:00Z",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    main = tmp_path / "main.jsonl"
    main.write_text(
        json.dumps(
            {
                "schema_version": "news_observation_v1",
                "observation_id": "00000000-0000-4000-8000-000000009999",
                "as_of_utc": "2026-05-01T08:00:00Z",
                "published_utc": "2026-05-01T08:00:00Z",
                "source_id": "seed_world",
                "canonical_text": "World seed row",
                "text_sha256": "a347d2d11e94363755918d1b93704f1d9f2fba79ef8a32e874dda1d0b0491f35",
                "ingested_at_utc": "2026-05-01T08:01:00Z",
                "dataset_partition": "train_holdout",
                "hypothesis_tag": "[HYPO]",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    out = tmp_path / "finance_only.jsonl"
    cp = subprocess.run(
        [
            sys.executable,
            str(INGEST_SCRIPT),
            "--external-feed-json",
            str(feed),
            "--output-jsonl",
            str(out),
            "--append-existing-jsonl",
            str(main),
            "--standalone",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stdout + cp.stderr
    rows = [json.loads(l) for l in out.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(rows) == 1
    assert "Finance headline" in rows[0]["canonical_text"]
    assert rows[0]["source_id"] == "external_feed_bbc_business"
