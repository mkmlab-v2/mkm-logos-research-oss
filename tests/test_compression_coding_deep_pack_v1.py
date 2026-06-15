"""Coding deep pack PoC: zone_f_code template catalog + twin gate (B-track)."""



from __future__ import annotations



import hashlib

import json

from pathlib import Path



import pytest



ROOT = Path(__file__).resolve().parents[1]

TEMPLATES = ROOT / "codebook/templates/zone_f_code_templates_v1.jsonl"

MANIFEST = ROOT / "codebook/templates/zone_f_code_templates_manifest_v1.json"

GATE = ROOT / "docs/final/artifacts/compression_coding_deep_pack_gate_v1_latest.json"

SIGNOFF = ROOT / "docs/final/artifacts/compression_coding_deep_pack_promotion_signoff_envelope_v1_latest.json"

CANDIDATE_POOL_SIGNOFF = ROOT / "docs/final/artifacts/compression_candidate_pool_on_promotion_signoff_envelope_v1_latest.json"

BUILDER = ROOT / "scripts/build_compression_coding_deep_pack_gate_v1.py"





def _load(path: Path) -> dict:

    return json.loads(path.read_text(encoding="utf-8"))





def _template_row_count() -> int:

    return sum(1 for line in TEMPLATES.read_text(encoding="utf-8").splitlines() if line.strip())





def test_zone_f_code_templates_manifest_matches_jsonl() -> None:

    assert TEMPLATES.is_file()

    assert MANIFEST.is_file()

    manifest = _load(MANIFEST)

    row_count = _template_row_count()

    assert manifest["schema"] == "zone_f_code_templates_manifest_v1"

    assert manifest["row_count"] == row_count

    h = hashlib.sha256(TEMPLATES.read_bytes()).hexdigest()

    assert manifest["catalog_sha256"] == h





def test_coding_deep_pack_gate_schema_and_twin_axes() -> None:

    assert GATE.is_file()

    assert BUILDER.is_file()

    gate = _load(GATE)

    row_count = _template_row_count()

    assert gate["schema"] == "compression_coding_deep_pack_gate_v1"

    assert gate["track_a_active_untouched"] is True

    assert gate["send_gate"] == "HOLD"

    assert gate["twin_metrics_axis"]["primary_pair"] == ["saving_rate", "exact_restore_ok"]

    assert gate["twin_metrics_axis"]["secondary_axis"] == "jaccard_proxy"

    assert "Tier A operational pass rate" in gate["tier_a_status_note"]

    assert gate["template_catalog"]["row_count"] == row_count

    assert gate.get("signoff_envelope") == "docs/final/artifacts/compression_coding_deep_pack_promotion_signoff_envelope_v1_latest.json"

    assert len(gate["cases"]) == row_count

    for case in gate["cases"]:

        assert case.get("roundtrip_path") == "template_catalog_wire_v1"

        assert "saving_rate" in case

        assert "exact_restore_ok" in case

        assert "jaccard_proxy" in case

    assert gate["summary"]["exact_restore_pass_count"] == row_count

    assert float(gate["summary"]["mean_saving_rate"]) > 0.0





def test_coding_deep_pack_signoff_envelope_separate_from_candidate_pool() -> None:

    assert SIGNOFF.is_file()

    doc = _load(SIGNOFF)

    assert doc["schema"] == "compression_coding_deep_pack_promotion_signoff_envelope_v1"

    assert doc["track_a_active_untouched"] is True

    assert doc["send_gate"] == "HOLD"

    assert doc["separate_from_candidate_pool_signoff"] == CANDIDATE_POOL_SIGNOFF.relative_to(ROOT).as_posix()

    assert "candidate_pool_on_headline_merge" in doc["forbidden_in_this_envelope"]

    assert doc["apply_command_after_signoff"] is None

    gates = doc["promotion_gates_at_apply"]

    assert gates["roundtrip_path"] == "template_catalog_wire_v1"

    assert gates["exact_restore_pass_count_observed"] == gates["exact_restore_pass_count_min"]





def test_coding_deep_pack_wire_codec_exact_restore() -> None:

    from scripts.compression_coding_deep_pack_v1_lib import (

        build_wire_packet,

        expand_template_wire,

        load_default_catalog,

        measure_template_wire_twin,

        wire_to_compact,

    )



    rows, catalog_sha256 = load_default_catalog()

    row = rows[0]

    wire = build_wire_packet(template_id=str(row["template_id"]), catalog_sha256=catalog_sha256)

    compact = wire_to_compact(wire)

    restored = expand_template_wire(compact, rows, expected_catalog_sha256=catalog_sha256)

    assert restored == row["snippet"]

    twin = measure_template_wire_twin(

        original_snippet=str(row["snippet"]),

        template_id=str(row["template_id"]),

        catalog_sha256=catalog_sha256,

        catalog_rows=rows,

    )

    assert twin["exact_restore_ok"] is True

    assert twin["jaccard_proxy"] == 1.0





def test_manifest_idempotent_when_catalog_unchanged() -> None:

    from scripts.build_compression_coding_deep_pack_gate_v1 import build_manifest



    before = _load(MANIFEST)["generated_at_utc"]

    rebuilt = build_manifest(TEMPLATES, MANIFEST)

    after = rebuilt["generated_at_utc"]

    assert after == before





def test_literal_slot_extract_and_roundtrip_unit() -> None:
    from scripts.compression_coding_deep_pack_v1_lib import (
        apply_literal_slot_renames,
        extract_literal_slots,
        load_template_catalog,
        measure_template_wire_twin,
        resolve_template_match,
    )

    rows = load_template_catalog(TEMPLATES)
    canonical = str(rows[0]["snippet"])
    variant = apply_literal_slot_renames(canonical, {"user_id": "account_id"})
    slots = extract_literal_slots(canonical, variant)
    assert slots == {"user_id": "account_id"}
    resolved = resolve_template_match(variant, rows)
    assert resolved == ("zf_t01", {"user_id": "account_id"})
    manifest = _load(MANIFEST)
    twin = measure_template_wire_twin(
        original_snippet=variant,
        template_id="zf_t01",
        catalog_sha256=str(manifest["catalog_sha256"]),
        catalog_rows=rows,
        literal_slots=slots,
    )
    assert twin["exact_restore_ok"] is True
    assert twin["saving_rate"] > 0.0


def test_coding_deep_pack_gate_regenerate_smoke() -> None:

    pytest.importorskip("fastapi")

    import subprocess

    import sys



    proc = subprocess.run(

        [sys.executable, str(BUILDER)],

        cwd=str(ROOT),

        capture_output=True,

        text=True,

        check=False,

    )

    assert proc.returncode == 0, proc.stderr or proc.stdout

