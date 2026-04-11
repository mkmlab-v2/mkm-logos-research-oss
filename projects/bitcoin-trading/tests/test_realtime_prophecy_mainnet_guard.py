"""Env gates for ProphecyStack + live order path (realtime_trading_with_monitoring)."""

import os
import unittest

from src.integration.realtime_trading_with_monitoring import (
    _block_live_orders_for_prophecy_fusion,
    _env_flag_true,
)


class TestProphecyMainnetGuard(unittest.TestCase):
    def tearDown(self) -> None:
        for k in (
            "DISABLE_PROPHECY_STACK",
            "PROPHECY_FUSION_ALLOW_MAINNET",
        ):
            os.environ.pop(k, None)

    def test_env_flag_true(self) -> None:
        os.environ["DISABLE_PROPHECY_STACK"] = "1"
        self.assertTrue(_env_flag_true("DISABLE_PROPHECY_STACK"))
        os.environ["DISABLE_PROPHECY_STACK"] = "true"
        self.assertTrue(_env_flag_true("DISABLE_PROPHECY_STACK"))
        os.environ.pop("DISABLE_PROPHECY_STACK", None)
        self.assertFalse(_env_flag_true("DISABLE_PROPHECY_STACK"))

    def test_block_when_mainnet_and_stack_and_no_override(self) -> None:
        os.environ.pop("PROPHECY_FUSION_ALLOW_MAINNET", None)
        self.assertTrue(_block_live_orders_for_prophecy_fusion(object(), testnet=False))

    def test_no_block_testnet(self) -> None:
        os.environ.pop("PROPHECY_FUSION_ALLOW_MAINNET", None)
        self.assertFalse(_block_live_orders_for_prophecy_fusion(object(), testnet=True))

    def test_no_block_without_stack(self) -> None:
        os.environ.pop("PROPHECY_FUSION_ALLOW_MAINNET", None)
        self.assertFalse(_block_live_orders_for_prophecy_fusion(None, testnet=False))

    def test_no_block_with_override(self) -> None:
        os.environ["PROPHECY_FUSION_ALLOW_MAINNET"] = "1"
        self.assertFalse(_block_live_orders_for_prophecy_fusion(object(), testnet=False))


if __name__ == "__main__":
    unittest.main()
