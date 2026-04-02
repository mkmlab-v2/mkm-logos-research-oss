"""
Chronos-Forward KOSPI baseline — reproducible CLI (workspace root on sys.path).

Outputs:
  training   -> data/chronos_forward_training/training_result.json
  holdout2026 -> data/chronos_forward_training/holdout_2026_result.json
  both       -> training, then holdout 2026 (two runs)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.prophecy.chronos_forward_trainer import ChronosForwardTrainer  # noqa: E402


def _run(save_interval: int, verbose: bool, holdout_year: Optional[int]) -> None:
    trainer = ChronosForwardTrainer()
    trainer.run_training(
        save_interval=save_interval,
        verbose=verbose,
        holdout_year=holdout_year,
    )


def main() -> int:
    p = argparse.ArgumentParser(description="Chronos-Forward KOSPI baseline")
    p.add_argument(
        "--mode",
        choices=("training", "holdout2026", "both"),
        default="both",
        help="training | holdout2026 | both (default: both)",
    )
    p.add_argument("--save-interval", type=int, default=50, dest="save_interval")
    p.add_argument("--quiet", action="store_true", help="set verbose=False on trainer")
    args = p.parse_args()
    verbose = not args.quiet

    if args.mode == "training":
        _run(args.save_interval, verbose, None)
    elif args.mode == "holdout2026":
        _run(args.save_interval, verbose, 2026)
    else:
        _run(args.save_interval, verbose, None)
        _run(args.save_interval, verbose, 2026)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
