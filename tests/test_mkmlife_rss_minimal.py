"""Tests for minimal RSS/Atom parsing."""

from tools.mkmlife.rss_minimal import parse_feed_items


def test_rss2_basic():
    xml = b"""<?xml version="1.0"?>
    <rss version="2.0"><channel>
      <item><title>Hello</title><link>https://example.com/a</link></item>
      <item><title>World</title><link>https://example.com/b</link></item>
    </channel></rss>"""
    items = parse_feed_items(xml)
    assert len(items) == 2
    assert items[0]["title"] == "Hello"
    assert items[1]["link"] == "https://example.com/b"


def test_atom_basic():
    xml = b"""<?xml version="1.0"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <entry>
        <title>Atom Title</title>
        <link href="https://example.com/x"/>
      </entry>
    </feed>"""
    items = parse_feed_items(xml)
    assert len(items) == 1
    assert items[0]["title"] == "Atom Title"
    assert items[0]["link"] == "https://example.com/x"


def test_invalid_xml():
    assert parse_feed_items(b"not xml") == []
