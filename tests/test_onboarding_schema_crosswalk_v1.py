"""P0 온보딩 스키마 통일 회귀 테스트.

두 온보딩 계약(mkm_consumer_profile_v1 정본 · mkm_study_onboarding_request_v1 단계뷰)이
하나의 SSOT 설문 팩과 단일 onboarding_stage 모델로 정합하는지, 그리고 앱 하위호환(3필드 유지)이
깨지지 않는지 고정한다. consumer_survey_only · research_only · [HYPO].
"""
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

CROSSWALK = ROOT / "docs/final/artifacts/onboarding_schema_crosswalk_v1.json"
CONSUMER_SCHEMA = ROOT / "docs/final/schemas/mkm_consumer_profile_v1.schema.json"
CONSUMER_EXAMPLE = ROOT / "docs/final/schemas/mkm_consumer_profile_v1.example.json"
ITEM_BANK = ROOT / "docs/final/artifacts/clinic_constitution_survey_item_bank_v1.json"
STUDY_PKG = ROOT / "packages/mkm-study-profile-contract/schema/onboarding-request-v1.schema.json"
STUDY_DOCS = ROOT / "docs/final/artifacts/schemas/mkm_study_onboarding_request_v1.schema.json"
STUDY_TS_CONTRACT = ROOT / "packages/mkm-study-profile-contract/src/index.ts"

STUDY_MINIMAL_FIELDS = {"stress_response", "change_preference", "sweat_recovery"}


def _load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def crosswalk():
    return _load(CROSSWALK)


@pytest.fixture(scope="module")
def bank():
    return _load(ITEM_BANK)


def test_crosswalk_declares_lane_and_research_only(crosswalk):
    assert crosswalk["schema"] == "onboarding_schema_crosswalk_v1"
    assert crosswalk["lane"] == "consumer_survey_only"
    assert crosswalk["research_only"] is True


def test_shared_pack_id_consistent_across_ssots(crosswalk, bank):
    pack = crosswalk["shared_survey"]["pack_id"]
    assert pack == "mkm_constitution_survey_core_v1"
    assert bank["pack_id"] == pack
    example = _load(CONSUMER_EXAMPLE)
    assert example["constitution"]["pack_id"] == pack


def test_item_bank_full_count_and_axes(crosswalk, bank):
    items = bank["items"]
    assert len(items) == crosswalk["shared_survey"]["expected_full_item_count"] == 22
    bank_axes = {it["axis"] for it in items}
    assert bank_axes == set(crosswalk["shared_survey"]["axes"])


def test_minimal_field_crosswalk_covers_three_study_fields(crosswalk):
    fields = {row["study_field"] for row in crosswalk["minimal_field_crosswalk"]}
    assert fields == STUDY_MINIMAL_FIELDS


def test_minimal_crosswalk_axes_and_items_exist(crosswalk, bank):
    valid_ids = {it["item_id"] for it in bank["items"]}
    valid_axes = set(crosswalk["shared_survey"]["axes"])
    for row in crosswalk["minimal_field_crosswalk"]:
        assert row["primary_axis"] in valid_axes, row
        assert row["related_item_ids"], row
        for iid in row["related_item_ids"]:
            assert iid in valid_ids, (row["study_field"], iid)


def test_study_schemas_are_identical():
    assert _load(STUDY_PKG) == _load(STUDY_DOCS)


def test_study_schema_backward_compat_and_additive():
    study = _load(STUDY_PKG)
    props = study["properties"]
    # 하위호환: 3필드 + onboarding_stage 유지
    survey_props = props["constitution_survey"]["properties"]
    assert STUDY_MINIMAL_FIELDS.issubset(set(survey_props))
    assert set(props["onboarding_stage"]["enum"]) == {"minimal", "birth_complete", "extended_complete"}
    # additive: 정본 팩 참조 + 22문항 응답 규격
    assert "constitution_pack_id" in props
    assert "constitution_responses" in props
    resp = props["constitution_responses"]["additionalProperties"]
    assert resp["type"] == "integer" and resp["minimum"] == 0 and resp["maximum"] == 4


def test_stage_model_matches_study_enum(crosswalk):
    study = _load(STUDY_PKG)
    stage_enum = set(study["properties"]["onboarding_stage"]["enum"])
    model_stages = {row["stage"] for row in crosswalk["onboarding_stage_model"]}
    assert model_stages == stage_enum


def test_ts_contract_in_sync_with_extended_schema():
    """TS 계약이 P0 확장 스키마(constitution_pack_id/responses)와 드리프트하지 않도록 고정."""
    src = STUDY_TS_CONTRACT.read_text(encoding="utf-8")
    study = _load(STUDY_PKG)
    props = study["properties"]
    assert "constitution_pack_id" in props and "constitution_responses" in props
    # wire(snake_case) + stored(camelCase) 양쪽에 반영되었는지
    assert "constitution_pack_id?" in src, "TS 계약 wire 타입에 constitution_pack_id 미반영"
    assert "constitution_responses?" in src, "TS 계약 wire 타입에 constitution_responses 미반영"
    assert "constitutionPackId?" in src, "TS 계약 stored 타입에 constitutionPackId 미반영"
    assert "constitutionResponses?" in src, "TS 계약 stored 타입에 constitutionResponses 미반영"


def test_consumer_response_scale_matches_study(crosswalk):
    consumer = _load(CONSUMER_SCHEMA)
    c_resp = consumer["properties"]["constitution"]["properties"]["responses"]["additionalProperties"]
    study = _load(STUDY_PKG)
    s_resp = study["properties"]["constitution_responses"]["additionalProperties"]
    assert (c_resp["minimum"], c_resp["maximum"]) == (s_resp["minimum"], s_resp["maximum"]) == (0, 4)


def test_crosswalk_pointer_present_in_schema_descriptions():
    for p in (CONSUMER_SCHEMA, STUDY_PKG, STUDY_DOCS):
        assert "onboarding_schema_crosswalk_v1" in _load(p)["description"]
