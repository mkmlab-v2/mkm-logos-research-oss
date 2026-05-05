#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Backward-compatible entry: Fact-Safe gate → webhook PoC only.

Delegates to ``run_conditional_action_gate_v1.py --backend webhook ...``.

For pluggable backends use ``run_conditional_action_gate_v1.py`` directly
(``--backend api`` for one-shot USD-M API order).
"""
from __future__ import annotations

import sys

# Re-export for tests and callers
from run_conditional_action_gate_v1 import evaluate_gate
from run_conditional_action_gate_v1 import main as _action_main


def main(argv: list[str] | None = None) -> int:
    a = list(argv) if argv is not None else sys.argv[1:]
    if "--backend" not in a:
        a = ["--backend", "webhook"] + a
    return _action_main(a)


if __name__ == "__main__":
    raise SystemExit(main())
