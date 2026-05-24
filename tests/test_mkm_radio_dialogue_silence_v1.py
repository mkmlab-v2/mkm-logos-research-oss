from scripts.mkm_radio_dialogue_silence_v1 import silence_ms_between


def test_persona_change_gap() -> None:
    assert silence_ms_between({"persona": "a"}, {"persona": "b", "copy_tags": []}) == 800
