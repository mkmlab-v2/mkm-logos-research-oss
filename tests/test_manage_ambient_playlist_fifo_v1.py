"""Ambient concat FIFO."""

from pathlib import Path

import scripts.manage_ambient_playlist_fifo_v1 as fifo


def test_init_and_append(tmp_path: Path) -> None:
    bed = tmp_path / "bed.wav"
    bed.write_bytes(b"RIFF" + b"\0" * 100)
    pl = tmp_path / "playlist.txt"
    st = tmp_path / "state.json"
    doc = fifo.init_fifo(tmp_path, bed, playlist_path=pl)
    assert len(doc["entries"]) == 1
    ev = tmp_path / "event.mp3"
    ev.write_bytes(b"\0" * 50)
    doc2 = fifo.append_event(tmp_path, ev, kind="zone_b", playlist_path=pl, state=doc)
    assert len(doc2["entries"]) == 2
    text = pl.read_text(encoding="utf-8")
    assert text.count("file '") == 2
