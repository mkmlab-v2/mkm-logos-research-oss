"""BigSet atypical human review queue stub + offline bench."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.bench_bigset_tier0_atypical_signal_v1 import evaluate_case
from scripts.detect_bigset_tier0_atypical_signal_v1 import detect

QUEUE_STUB = ROOT / "scripts/bigset_tier0_atypical_human_review_queue_stub_v1.py"
BENCH = ROOT / "scripts/bench_bigset_tier0_atypical_signal_v1.py"
CASES = ROOT / "tests/fixtures/bigset/atypical_bench_cases_v1.json"
FIXTURE = ROOT / "tests/fixtures/bigset/sample_theology_tier0_rows_v1.csv"
ATYPICAL = ROOT / "scripts/detect_bigset_tier0_atypical_signal_v1.py"


def _load_queue_mod():
    spec = importlib.util.spec_from_file_location("bigset_review_queue_stub", QUEUE_STUB)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_queue_enqueue_from_signals(tmp_path: Path):
    mod = _load_queue_mod()
    root = tmp_path / "ws"
    root.mkdir()
    sig_path = root / "signals.json"
    sig_doc = detect(
        [
            {
                "verse_ref": "Gen.6.1",
                "conflict_group_id": "G1",
                "school_tier": "historical_criticism",
            },
            {
                "verse_ref": "Gen.6.2",
                "conflict_group_id": "G1",
                "school_tier": "judaic_mysticism",
            },
            {
                "verse_ref": "Gen.6.3",
                "conflict_group_id": "G1",
                "school_tier": "historical_criticism",
            },
        ]
    )
    sig_path.write_text(json.dumps(sig_doc, ensure_ascii=False), encoding="utf-8")
    queue_path = tmp_path / "queue.jsonl"

    proc = subprocess.run(
        [
            sys.executable,
            str(QUEUE_STUB),
            "--root",
            str(root),
            "enqueue-from-signals",
            "--signals-json",
            str(sig_path),
            "--queue-path",
            str(queue_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    lines = queue_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) >= 1
    row = json.loads(lines[0])
    assert row["schema"] == mod.QUEUE_ENTRY_SCHEMA
    assert row["status"] == "pending_human_review"
    assert row["send_gate"] == "HOLD"


def test_queue_export_pending(tmp_path: Path):
    mod = _load_queue_mod()
    root = tmp_path / "ws"
    root.mkdir()
    queue_path = tmp_path / "queue.jsonl"
    ent = mod.build_queue_entry_v0(
        review_id="rid1",
        signal={"signal_type": "school_tier_island", "conflict_group_id": "G1", "row_index": 1},
        queued_at_utc="2026-06-24T00:00:00Z",
        signals_json_path=root / "signals.json",
        source_csv_path=None,
        root=root,
    )
    mod.append_queue_line(queue_path, ent)
    out = root / "pending.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(QUEUE_STUB),
            "--root",
            str(root),
            "export-pending",
            "--queue-path",
            str(queue_path),
            "--out",
            str(out),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == mod.EXPORT_PENDING_SCHEMA
    assert doc["pending_count"] == 1


def test_bench_cases_all_pass():
    cases = json.loads(CASES.read_text(encoding="utf-8"))
    for case in cases:
        result = evaluate_case(case)
        assert result["ok"], result


def test_bench_cli_exit_zero(tmp_path: Path):
    proc = subprocess.run(
        [
            sys.executable,
            str(BENCH),
            "--cases",
            str(CASES),
            "--out",
            str(tmp_path / "bench.json"),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_ingest_chain_enqueues_when_signals(tmp_path: Path):
    """Smoke: fixture may yield zero signals; enqueue step still exit 0."""
    sig_out = tmp_path / "sig.json"
    proc = subprocess.run(
        [sys.executable, str(ATYPICAL), "--csv", str(FIXTURE), "--out", str(sig_out)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    queue_path = tmp_path / "q.jsonl"
    proc2 = subprocess.run(
        [
            sys.executable,
            str(QUEUE_STUB),
            "--root",
            str(ROOT),
            "enqueue-from-signals",
            "--signals-json",
            str(sig_out),
            "--source-csv",
            str(FIXTURE),
            "--queue-path",
            str(queue_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc2.returncode == 0, proc2.stderr or proc2.stdout
