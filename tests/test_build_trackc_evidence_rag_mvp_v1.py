from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_trackc_evidence_rag_mvp_v1.py"


def test_trackc_evidence_rag_mvp_emits_ranked_results(tmp_path: Path) -> None:
    md = tmp_path / "plan.md"
    md.write_text("# Track C Plan\n\nB2B commercialization and KPI contract.\n", encoding="utf-8")
    js = tmp_path / "ops.json"
    js.write_text(
        json.dumps({"schema": "ops_v1", "status": "GREEN", "generated_at_utc": "2099-01-01T00:00:00Z"}),
        encoding="utf-8",
    )
    out = tmp_path / "out.json"
    catalog = tmp_path / "catalog.json"
    catalog.write_text(
        json.dumps(
            {
                "catalog": [
                    {
                        "id": "plan",
                        "title": "Track C Business Plan",
                        "path": str(md),
                        "tags": ["trackc", "commercialization", "b2b", "kpi"],
                    },
                    {
                        "id": "ops",
                        "title": "Ops Audit",
                        "path": str(js),
                        "tags": ["ops", "security", "audit"],
                    },
                    {
                        "id": "missing_doc",
                        "title": "Missing Doc",
                        "path": str(tmp_path / "missing.md"),
                        "tags": ["trackc", "proof"],
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--workspace-root",
            str(ROOT),
            "--catalog-json",
            str(catalog),
            "--query",
            "trackc commercialization proof",
            "--query",
            "ops security status",
            "--output-json",
            str(out),
            "--max-evidence",
            "2",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stdout + cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "trackc_evidence_rag_mvp_v1"
    assert doc.get("research_only") is True
    queries = doc.get("queries")
    assert isinstance(queries, list) and len(queries) == 2
    q1 = queries[0]
    q2 = queries[1]
    assert q1["results"][0]["id"] in {"plan", "missing_doc"}
    assert any(r["id"] == "ops" for r in q2["results"])
    missing_rows = [r for r in q1["results"] + q2["results"] if r["id"] == "missing_doc"]
    if missing_rows:
        assert missing_rows[0]["exists"] is False
