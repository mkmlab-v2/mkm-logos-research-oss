from scripts.validate_track_c_landing_claims_v1 import validate_claims


def test_validate_claims_passes_with_required_disclaimer():
    lines = [
        "This is a risk warning service.",
        "Not investment advice. Final decisions remain with clients.",
        "Scenario posture and early warning only.",
    ]
    errors = validate_claims(lines, required_disclaimer="Not investment advice. Final decisions remain with clients.")
    assert errors == []


def test_validate_claims_detects_forbidden_claims():
    lines = [
        "Guaranteed returns with buy now signal.",
        "risk warning",
        "not investment advice",
    ]
    errors = validate_claims(lines, required_disclaimer="not investment advice")
    assert any("forbidden claim pattern matched" in e for e in errors)

