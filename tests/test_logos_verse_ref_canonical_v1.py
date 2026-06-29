# -*- coding: utf-8 -*-
from scripts.logos_verse_ref_canonical_v1 import canonical_verse_ref


def test_canonical_aliases() -> None:
    assert canonical_verse_ref("vr_1chr_12_32") == "1Chr.12.32"
    assert canonical_verse_ref("hebrew::1Chronicles.12.32") == "1Chr.12.32"
    assert canonical_verse_ref("aramaic::Daniel.5.25") == "Dan.5.25"
    assert canonical_verse_ref("verse_ref:daniel_5_25_28") == "Dan.5.25"
    assert canonical_verse_ref("hebrew::Nehemiah.4.9") == "Neh.4.9"
    assert canonical_verse_ref("ps119.86") == "Ps.119.86"
    assert canonical_verse_ref("node:verse_psalm_27_14") == "Ps.27.14"
    assert canonical_verse_ref("verse_prov_22_3") == "Prov.22.3"
    assert canonical_verse_ref("lam.3.21-24") == "Lam.3.21"
    assert canonical_verse_ref("Ref:psalm.103.8") == "Ps.103.8"
    assert canonical_verse_ref("Lamentations_3.22.23") == "Lam.3.22"
    assert canonical_verse_ref("John.19.34") == "Jhn.19.34"
    assert canonical_verse_ref("Exo.16.15") == "Exod.16.15"
