"""Label helpers for OrbGraphBloom canvas (mirrors magic-orb-graph-bloom.ts)."""


def humanize_bloom_verse_ref(ref: str):
    t = ref.strip()
    import re

    ps = re.match(r"^Ps\.?(\d+)\.(\d+)$", t, re.I)
    if ps:
        return f"시편 {ps.group(1)}:{ps.group(2)}"
    jer = re.match(r"^Jer\.?(\d+)\.(\d+)$", t, re.I)
    if jer:
        return f"예레미야 {jer.group(1)}:{jer.group(2)}"
    return None


def should_skip_bloom_canvas_label(node_label: str, seed_query: str | None) -> bool:
    label = node_label.strip()
    seed = (seed_query or "").strip()
    if not label or not seed or len(label) < 6:
        return False
    if label in seed or seed.startswith(label[: min(24, len(label))]):
        return True
    if label in seed or seed[: min(24, len(seed))] in label:
        return True
    return False


def test_humanize_ps_ref():
    assert humanize_bloom_verse_ref("Ps.89.28") == "시편 89:28"


def test_skip_label_when_duplicates_pill_query():
    seed = "위기 가운데 언약의 안정과 신실"
    assert should_skip_bloom_canvas_label("위기 가운데 언약의 안정", seed) is True


def test_keep_verse_label():
    assert should_skip_bloom_canvas_label("시편 89:28", "위기 가운데 언약의 안정과 신실") is False
