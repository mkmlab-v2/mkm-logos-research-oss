from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "docs/final/schemas/lens_multi_axis_audit_envelope_v1.schema.json"
BUILDER = ROOT / "scripts/build_lens_multi_axis_audit_envelope_v1.py"
FUSION = ROOT / "scripts/build_cross_lens_rag_fusion_v1.py"
AUDIT_MOD = ROOT / "scripts/lens_multi_axis_audit_v1.py"


def _load_schema() -> dict:
    return json.loads(SCHEMA.read_text(encoding="utf-8"))


def test_extract_axes_from_fixture_lens_files() -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    from lens_multi_axis_audit_v1 import build_envelope_from_lens_paths

    my = ROOT / "docs/final/artifacts/myeongni_independent_lens_latest.json"
    sa = ROOT / "docs/final/artifacts/sasang_independent_lens_latest.json"
    if not my.is_file() or not sa.is_file():
        pytest.skip("latest lens artifacts missing")

    env = build_envelope_from_lens_paths(my, sa, interpret_path=None)
    jsonschema.validate(env, _load_schema())
    assert env["graph_router_invoked"] is False
    assert env["graph_merge_forbidden"] is True
    assert env["lint"]["pass"] is True
    my_axes = env["lenses"]["myeongni"]["axes"]
    sa_axes = env["lenses"]["sasang"]["axes"]
    assert any(a["axis_id"] == "fusion_direction_scores" for a in my_axes)
    assert any(a["axis_id"] == "b_track_axis_scores_v1" for a in sa_axes)


def test_builder_cli_writes_latest(tmp_path: Path) -> None:
    my = ROOT / "docs/final/artifacts/myeongni_independent_lens_latest.json"
    sa = ROOT / "docs/final/artifacts/sasang_independent_lens_latest.json"
    if not my.is_file() or not sa.is_file():
        pytest.skip("latest lens artifacts missing")
    out = tmp_path / "envelope.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(BUILDER),
            "--myeongni-lens",
            str(my),
            "--sasang-lens",
            str(sa),
            "--no-interpret",
            "--out-json",
            str(out),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    jsonschema.validate(doc, _load_schema())


def test_fusion_embeds_multi_axis_audit_v1(tmp_path: Path) -> None:
    logos_wealth = tmp_path / "logos_wealth.json"
    logos_justice = tmp_path / "logos_justice.json"
    logos_empire = tmp_path / "logos_empire.json"
    fusion_stub = tmp_path / "fusion_stub.json"
    myeongni = tmp_path / "myeongni.json"
    sasang = tmp_path / "sasang.json"
    logos_lens = tmp_path / "logos.json"
    out_json = tmp_path / "fusion_out.json"

    theme_doc = {"top_k": [{"verse_id": "v1", "score": 0.4}], "ts_utc": "2099-01-01T00:00:00Z"}
    for p, doc in [
        (logos_wealth, theme_doc),
        (logos_justice, theme_doc),
        (logos_empire, theme_doc),
        (fusion_stub, {"consensus": {"consensus_sign": "bull"}}),
    ]:
        p.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    myeongni.write_text(
        json.dumps(
            {
                "schema": "myeongni_independent_lens_v0",
                "lens_id": "myeongni",
                "scores": {"direction_score": 0.2, "confidence": 0.8},
                "myeongni_b_track_quant_block_v0": {"schema": "x", "status": "ok"},
                "ts_utc": "2099-01-01T00:00:00Z",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    sasang.write_text(
        json.dumps(
            {
                "schema": "sasang_independent_lens_v0",
                "lens_id": "sasang",
                "scores": {"direction_score": 0.1, "confidence": 0.6},
                "b_track_axis_scores_v1": {
                    "schema": "sasang_b_track_axis_scores_v1",
                    "heat_proxy": 0.7,
                    "cold_proxy": 0.3,
                },
                "ts_utc": "2099-01-01T00:00:00Z",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    logos_lens.write_text(
        json.dumps(
            {
                "schema": "logos_independent_lens_v0",
                "lens_id": "logos",
                "scores": {"direction_score": 0.05, "confidence": 0.4},
                "ts_utc": "2099-01-01T00:00:00Z",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    cp = subprocess.run(
        [
            sys.executable,
            str(FUSION),
            "--logos-wealth",
            str(logos_wealth),
            "--logos-justice",
            str(logos_justice),
            "--logos-empire",
            str(logos_empire),
            "--fusion-stub",
            str(fusion_stub),
            "--myeongni-lens",
            str(myeongni),
            "--sasang-lens",
            str(sasang),
            "--logos-lens",
            str(logos_lens),
            "--no-market-sasang",
            "--no-market-myeongni",
            "--out-json",
            str(out_json),
            "--skip-history-append",
            "--skip-alert-emit",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr
    fusion = json.loads(out_json.read_text(encoding="utf-8"))
    assert fusion["version"] == "1.2.0"
    audit = fusion.get("lens_multi_axis_audit_v1")
    assert isinstance(audit, dict)
    assert audit.get("graph_router_invoked") is False
    jsonschema.validate(audit, _load_schema())


def test_lint_catches_forbidden_toe_phrase() -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    from lens_multi_axis_audit_v1 import lint_text_blob

    hits = lint_text_blob("이것은 단일 만물이론 완성입니다")
    assert "단일 만물이론" in hits
