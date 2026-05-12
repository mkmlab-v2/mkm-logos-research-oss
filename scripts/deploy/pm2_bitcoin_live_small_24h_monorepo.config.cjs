/**
 * PM2: bitcoin 24h live — 모노레포 SSOT 배치
 * cwd = 모노레포 루트, script = projects/bitcoin-trading/start_live_trading.py
 * 비밀(BINANCE 등)은 PM2에 두지 않고 레포 루트 또는 projects/bitcoin-trading/.env
 *
 * 사용: pm2 start /path/to/pm2_bitcoin_live_small_24h_monorepo.config.cjs
 */
module.exports = {
  apps: [
    {
      name: "bitcoin-live-small-24h",
      cwd: "/opt/mkm-destiny-ai-41e38ec6",
      script: "projects/bitcoin-trading/start_live_trading.py",
      interpreter: "python3",
      env: {
        PYTHONUNBUFFERED: "1",
        ENABLE_TRADING: "true",
        SYMBOL: "BTCUSDT",
        BTC_FUTURES_ENGINE: "aroon_v1",
        AROON_POLL_SEC: "20",
        AROON_ORDER_QTY: "0.001",
        AROON_LENS_MIN_CONF: "0.55",
        AROON_LENS_FILTER_ENABLED: "1",
        AROON_LENS_FILTER_MODE: "blocking",
        AROON_MIN_CROSS_GAP: "0.5",
        AROON_PERIOD: "14",
        AROON_KLINE_INTERVAL: "5m",
        AROON_LENS_SIGNAL_JSON:
          "/opt/mkm-destiny-ai-41e38ec6/docs/final/artifacts/btrack_hypothesis_prophecy_latest.json",
      },
    },
  ],
};
