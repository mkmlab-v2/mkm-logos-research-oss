"""JSON Schema validation for Bible insight candidates, survivor eval/candidates, and insight-cap bucket artifacts (CLI subprocess)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

try:
    import jsonschema
except ImportError:  # pragma: no cover
    jsonschema = None  # type: ignore[assignment]


def _load_schema(name: str) -> dict:
    return json.loads((ROOT / "docs" / "final" / "schemas" / name).read_text(encoding="utf-8"))


def _run_py(args: list[str], *, cwd: Path | None = None) -> None:
    proc = subprocess.run(
        [sys.executable, *args],
        cwd=str(cwd or ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout


@pytest.mark.skipif(jsonschema is None, reason="jsonschema not installed")
def test_insight_pipeline_and_cap_bucket_cli_outputs_validate(tmp_path: Path) -> None:
    s_candidates = _load_schema("bible_meaning_insight_candidates_v1.schema.json")
    s_eval = _load_schema("insight_survivor_eval_v1.schema.json")
    s_surv = _load_schema("insight_survivor_candidates_v1.schema.json")
    s_sweep = _load_schema("aramaic_insight_cap_bucket_threshold_sweep_v1.schema.json")
    s_rec = _load_schema("aramaic_insight_cap_bucket_threshold_recommendation_v1.schema.json")
    s_hist = _load_schema("aramaic_insight_cap_bucket_threshold_history_row_v1.schema.json")

    nodes = tmp_path / "nodes.jsonl"
    edges = tmp_path / "edges.jsonl"
    insight_out = tmp_path / "insight.json"
    eval_out = tmp_path / "eval.json"
    surv_out = tmp_path / "survivors.json"
    sweep_out = tmp_path / "sweep.json"
    rec_out = tmp_path / "rec.json"
    hist = tmp_path / "history.jsonl"

    n = {"node_id": "aramaic::Dan.2.4", "regime_tags": ["imperial"]}
    e = {"src_node_id": "aramaic::Dan.2.4", "dst_node_id": "aramaic::Dan.2.5"}
    nodes.write_text(json.dumps(n, ensure_ascii=False) + "\n", encoding="utf-8")
    edges.write_text(json.dumps(e, ensure_ascii=False) + "\n", encoding="utf-8")

    _run_py(
        [
            str(ROOT / "scripts" / "extract_bible_meaning_insight_candidates_v1.py"),
            "--nodes-jsonl",
            str(nodes),
            "--edges-jsonl",
            str(edges),
            "--output-json",
            str(insight_out),
        ]
    )
    doc_ins = json.loads(insight_out.read_text(encoding="utf-8"))
    jsonschema.validate(instance=doc_ins, schema=s_candidates)

    _run_py(
        [
            str(ROOT / "scripts" / "build_insight_survivor_eval_v1.py"),
            "--insight-json",
            str(insight_out),
            "--output-json",
            str(eval_out),
        ]
    )
    doc_eval = json.loads(eval_out.read_text(encoding="utf-8"))
    jsonschema.validate(instance=doc_eval, schema=s_eval)

    _run_py(
        [
            str(ROOT / "scripts" / "select_insight_survivor_candidates_v1.py"),
            "--eval-json",
            str(eval_out),
            "--output-json",
            str(surv_out),
            "--top-n",
            "5",
        ]
    )
    doc_surv = json.loads(surv_out.read_text(encoding="utf-8"))
    jsonschema.validate(instance=doc_surv, schema=s_surv)

    _run_py(
        [
            str(ROOT / "scripts" / "sweep_aramaic_insight_cap_bucket_thresholds_v1.py"),
            "--output-json",
            str(sweep_out),
        ]
    )
    doc_sweep = json.loads(sweep_out.read_text(encoding="utf-8"))
    jsonschema.validate(instance=doc_sweep, schema=s_sweep)

    _run_py(
        [
            str(ROOT / "scripts" / "apply_aramaic_insight_cap_bucket_threshold_recommendation_v1.py"),
            "--sweep-json",
            str(sweep_out),
            "--output-json",
            str(rec_out),
        ]
    )
    doc_rec = json.loads(rec_out.read_text(encoding="utf-8"))
    jsonschema.validate(instance=doc_rec, schema=s_rec)

    _run_py(
        [
            str(ROOT / "scripts" / "report_aramaic_insight_cap_threshold_history_v1.py"),
            "--recommended-json",
            str(rec_out),
            "--history-jsonl",
            str(hist),
        ]
    )
    lines = [ln for ln in hist.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 1
    row = json.loads(lines[0])
    jsonschema.validate(instance=row, schema=s_hist)
