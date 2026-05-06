from scripts.report_high_reliability_mode_gate import entry16_ready_for_manual_review


def test_entry16_direct_path() -> None:
    assert entry16_ready_for_manual_review(
        {
            "decision": "promote_candidate",
            "status": "candidate_ready_for_manual_review",
        }
    )


def test_entry16_proxy_path() -> None:
    assert entry16_ready_for_manual_review(
        {
            "decision": "promote_proxy_candidate_manual",
            "status": "proxy_candidate_ready_for_manual_review",
        }
    )


def test_entry16_rejects_incomplete() -> None:
    assert not entry16_ready_for_manual_review(
        {
            "decision": "hold",
            "status": "none",
        }
    )
