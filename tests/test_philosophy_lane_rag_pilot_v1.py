"""Contract smoke for philosophy_lane_rag_pilot_v1 (forbidden gate + JSON shape)."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


def test_philosophy_lane_forbidden_rejection() -> None:
    ws = Path(__file__).resolve().parents[1]
    script = ws / "scripts" / "philosophy_lane_rag_pilot_v1.py"
    assert script.is_file()
    proc = subprocess.run(
        [
            sys.executable,
            str(script),
            "--user-query",
            "비트코인 매수 타이밍 알려줘",
            "--out",
            str(ws / "docs" / "final" / "artifacts" / "_test_philosophy_lane_pilot_forbidden.json"),
        ],
        cwd=str(ws),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    out = ws / "docs" / "final" / "artifacts" / "_test_philosophy_lane_pilot_forbidden.json"
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "philosophy_lane_rag_pilot_v1"
    assert doc.get("status") == "fallback_rejection"
    assert any("forbidden" in str(x) for x in doc.get("reasons", []))
    assert doc.get("promotion_status") == "local_only_human_signoff_required"
    rails = doc.get("rails_used") or []
    assert "forbidden_substrings_v1" in rails


def test_philosophy_lane_schema_ok_without_sqlite() -> None:
    ws = Path(__file__).resolve().parents[1]
    script = ws / "scripts" / "philosophy_lane_rag_pilot_v1.py"
    proc = subprocess.run(
        [
            sys.executable,
            str(script),
            "--user-query",
            "요즘 마음이 복잡한데 차분해지는 생각을 알려줘",
            "--sqlite",
            str(ws / "docs" / "final" / "artifacts" / "_nonexistent_ann_lite.sqlite"),
            "--out",
            str(ws / "docs" / "final" / "artifacts" / "_test_philosophy_lane_pilot_no_sqlite.json"),
        ],
        cwd=str(ws),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    out = ws / "docs" / "final" / "artifacts" / "_test_philosophy_lane_pilot_no_sqlite.json"
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "philosophy_lane_rag_pilot_v1"
    assert doc.get("status") in ("ann_lite_skipped", "ok")
    assert isinstance(doc.get("blocks"), list)


def test_philosophy_lane_structured_bilingual_hybrid_dual() -> None:
    ws = Path(__file__).resolve().parents[1]
    st_sqlite = ws / "reports/constitution/btrack_pilot/logos_vector_index_ann_lite_st_u_v1.sqlite"
    if not st_sqlite.is_file():
        return
    script = ws / "scripts/philosophy_lane_rag_pilot_v1.py"
    out = ws / "reports/constitution/btrack_pilot/_test_philosophy_lane_structured_hybrid.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(script),
            "--query-en",
            "covenant stability under crisis",
            "--query-ko",
            "위기 가운데 언약의 안정과 신실",
            "--rag-lane",
            "hybrid_dual",
            "--hybrid-style",
            "dual_embed_mean",
            "--out",
            str(out),
        ],
        cwd=str(ws),
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    route = doc.get("rag_query_route") or {}
    assert route.get("structured_bilingual") is True
    assert route.get("hybrid_style") == "dual_embed_mean"
    assert doc.get("version") == "1.2.0"
    ann = doc.get("ann_lite_query") or {}
    assert isinstance(ann.get("top_k"), list) and ann["top_k"]


def test_philosophy_lane_custom_forbidden_config() -> None:
    ws = Path(__file__).resolve().parents[1]
    script = ws / "scripts" / "philosophy_lane_rag_pilot_v1.py"
    token = "mkm_philosophy_test_forbidden_token_xyz"
    cfg = {
        "schema": "philosophy_lane_rag_pilot_forbidden_substrings_v1",
        "version": "1.0.0",
        "substrings": [token],
    }
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".json",
        delete=False,
        encoding="utf-8",
    ) as tmp:
        json.dump(cfg, tmp)
        tmp_path = Path(tmp.name)
    out = ws / "docs" / "final" / "artifacts" / "_test_philosophy_lane_pilot_custom_forbidden.json"
    try:
        proc = subprocess.run(
            [
                sys.executable,
                str(script),
                "--user-query",
                f"Tell me about {token} please",
                "--forbidden-config",
                str(tmp_path),
                "--sqlite",
                str(ws / "docs" / "final" / "artifacts" / "_nonexistent_ann_lite.sqlite"),
                "--out",
                str(out),
            ],
            cwd=str(ws),
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert proc.returncode == 0, proc.stderr + proc.stdout
        doc = json.loads(out.read_text(encoding="utf-8"))
        assert doc.get("status") == "fallback_rejection"
        assert any(token in str(x) for x in doc.get("reasons", []))
    finally:
        tmp_path.unlink(missing_ok=True)
