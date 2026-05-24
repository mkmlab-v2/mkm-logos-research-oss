"""Science narrative forbidden patterns on mkm_radio Zone B copy."""

from scripts.mkm_radio_dialogue_guard_v1 import scan_forbidden


def test_sanitized_fuel_lines_pass():
    text = (
        "비계산적 의식 가설처럼 페이싱만 참고하십시오. "
        "잇프롬빗 명제는 시사하는 가설입니다. "
        "인지 과부하 신호일 수 있으니 브레이크를 권합니다."
    )
    assert scan_forbidden(text) == []


def test_quantum_proof_veto():
    assert "science_quantum_proof" in scan_forbidden("양자역학으로 입증했다")


def test_afterlife_veto():
    assert "science_afterlife" in scan_forbidden("사후세계 존재가 증명되었다")
