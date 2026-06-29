"""jemaai.cloud public showroom URL SSOT (observe canonical + legacy pixel demos)."""

from __future__ import annotations

JEMAAI_CLOUD = "https://jemaai.cloud"
JEMAAI_API = "https://api.jemaai.cloud"
OBSERVE_V1 = f"{JEMAAI_CLOUD}/public_observe_v1.html"
LEGACY_PREFIX = f"{JEMAAI_CLOUD}/legacy"


def legacy_html(filename: str) -> str:
    name = filename if filename.endswith(".html") else f"{filename}.html"
    return f"{LEGACY_PREFIX}/{name}"


# Common legacy demo entry points (B-track / internal only — not public default)
ORACLE_V6_PRODUCT = f"{LEGACY_PREFIX}/public_showroom_logos_oracle_v6.html?product=1"
MEANING_TOPOLOGY_GRAPH = legacy_html("public_showroom_meaning_topology_graph_v1.html")
TOPOLOGY_RADAR = legacy_html("public_showroom_topology_radar_v1.html")
BOARD_MINIMAL_LEGACY = legacy_html("public_showroom_board_minimal.html")

PUBLIC_EVENTS_LATEST = f"{JEMAAI_API}/api/public-events/latest"
