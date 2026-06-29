from __future__ import annotations

from scripts.run_truthfulqa_ab_benchmark_v1 import _parse_letter


def test_parse_letter_single_char() -> None:
    assert _parse_letter("B", 4) == "B"


def test_parse_letter_explicit_final_answer() -> None:
    text = "Thinking...\nFinal answer: D"
    assert _parse_letter(text, 4) == "D"


def test_parse_letter_ignores_letters_inside_words() -> None:
    text = "Evaluate the Choices based on Europe and England."
    assert _parse_letter(text, 4) is None


def test_parse_letter_isolated_choice_mentions() -> None:
    text = "Option A is wrong. The correct choice is C because factuality."
    assert _parse_letter(text, 4) == "C"
