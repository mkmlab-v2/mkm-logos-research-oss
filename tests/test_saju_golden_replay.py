import json
from pathlib import Path

from scripts.saju_dual_verify import VerifyInput, verify_dual_saju


def test_saju_golden_replay_status_and_reasons():
    fixture_path = Path("tests/fixtures/saju_golden_cases_v1.json")
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert payload["schema"] == "saju_golden_cases_v1"
    case_ids = {case["id"] for case in payload["cases"]}
    assert "kr_confirmed_reference_1973_1210_0430" in case_ids
    assert "kr_confirmed_non_boundary_1973_1209_0430" in case_ids
    assert "kr_confirmed_zi23_policy_1973_1210_2331" in case_ids

    for case in payload["cases"]:
        doc = verify_dual_saju(VerifyInput(**case["input"]))
        expected = case["expected"]
        assert doc["comparison"]["status"] == expected["status"], case["id"]
        for reason in expected.get("reasons_contains", []):
            assert reason in doc["comparison"]["reasons"], case["id"]
