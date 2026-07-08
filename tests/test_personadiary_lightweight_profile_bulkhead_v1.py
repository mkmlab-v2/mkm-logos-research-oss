"""PersonaDiary 경량 비임상 프로필 격벽 회귀 테스트.

PersonaDiary(Track C · preview_only)는 정본 mkm_consumer_profile_v1의 로컬 전용
부분집합만 사용한다: basic + 체질설문(core-5 게이팅). 임상 anthropometrics/health_basics는
절대 수집·저장하지 않으며, mkmlife API/DB/결제와 합선하지 않는다(localStorage 캐시 전용).

이 불변식을 고정해, 누군가 personadiary 프로필에 임상 필드나 mkmlife 네트워크 합선을
추가하면 CI가 잡도록 한다. consumer_survey_only · research_only · [HYPO].
"""
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

CROSSWALK = ROOT / "docs/final/artifacts/onboarding_schema_crosswalk_v1.json"
PD_PROFILE_LIB = ROOT / "projects/no1kmedi/src/lib/personadiaryConsumerProfileV1.ts"
PD_PACK = ROOT / "projects/no1kmedi/public/data/clinic_constitution_survey_pack_v1.json"

CLINICAL_FIELDS = ("anthropometrics", "health_basics")


def _load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def crosswalk():
    return _load(CROSSWALK)


@pytest.fixture(scope="module")
def view(crosswalk):
    assert "personadiary_local_view" in crosswalk, "크로스워크에 personadiary_local_view 미정의"
    return crosswalk["personadiary_local_view"]


@pytest.fixture(scope="module")
def profile_src():
    return PD_PROFILE_LIB.read_text(encoding="utf-8")


def test_view_is_local_preview_only_track_c(view):
    assert view["schema"] == "mkm_consumer_profile_v1"
    assert view["track"] == "C"
    assert view["preview_only"] is True
    assert view["storage"]["medium"] == "browser_localStorage"
    assert view["storage"]["server_upload"] is False


def test_view_excludes_clinical_fields(view):
    excluded = set(view["excludes_clinical"])
    assert set(CLINICAL_FIELDS).issubset(excluded)
    # collects 목록에 임상 필드가 새어들지 않았는지
    collected = " ".join(view["collects"])
    for field in CLINICAL_FIELDS:
        assert field not in collected, f"personadiary collects에 임상 필드 유입: {field}"


def test_view_shares_unified_pack(view, crosswalk):
    assert view["shared_pack_id"] == crosswalk["shared_survey"]["pack_id"] == "mkm_constitution_survey_core_v1"


def test_view_app_ref_points_to_real_lib(view):
    assert view["app_ref"] == "projects/no1kmedi/src/lib/personadiaryConsumerProfileV1.ts"
    assert PD_PROFILE_LIB.exists(), "personadiary 프로필 lib 파일 부재"


def test_profile_lib_has_no_clinical_fields(profile_src):
    for field in CLINICAL_FIELDS:
        assert field not in profile_src, f"personadiary 프로필 lib에 임상 필드 정의: {field}"


def test_profile_lib_is_local_only_no_mkmlife_network(profile_src):
    # 로컬 캐시 전용: 실제 네트워크 호출·원격 API 합선 패턴 금지
    assert "fetch(" not in profile_src, "personadiary 프로필 lib에 네트워크 fetch 유입"
    assert "XMLHttpRequest" not in profile_src, "personadiary 프로필 lib에 XHR 유입"
    assert "https://" not in profile_src, "personadiary 프로필 lib에 원격 URL 합선 유입"
    assert "@/app/api" not in profile_src, "personadiary 프로필 lib에 API 라우트 import 유입"
    # 격벽 의도 주석 + localStorage 전용 저장 근거
    assert "no mkmlife API" in profile_src, "격벽 의도 주석(no mkmlife API) 부재"
    assert "localStorage" in profile_src
    assert 'MKM_CONSUMER_PROFILE_CACHE_KEY = "mkm_consumer_profile_v1"' in profile_src


def test_profile_lib_declares_research_and_survey_lane(profile_src):
    assert 'MKM_CONSUMER_PROFILE_LANE = "consumer_survey_only"' in profile_src
    assert re.search(r"research_only\s*:\s*true", profile_src), "research_only:true 불변식 부재"


def test_public_pack_matches_unified_and_is_leak_safe():
    pack = _load(PD_PACK)
    assert pack["pack_id"] == "mkm_constitution_survey_core_v1"
    assert len(pack["items"]) == 22
    # core-5 게이팅 항목 존재
    assert len(pack["core_item_ids"]) == 5
    core = set(pack["core_item_ids"])
    ids = {it["item_id"] for it in pack["items"]}
    assert core.issubset(ids)
    # crown-jewel(가중치·힌트)이 공개 팩에 새지 않았는지
    for it in pack["items"]:
        assert "weight" not in it, f"공개 팩 항목에 weight 누출: {it.get('item_id')}"
        assert "constitution_hints" not in it, f"공개 팩 항목에 hints 누출: {it.get('item_id')}"
