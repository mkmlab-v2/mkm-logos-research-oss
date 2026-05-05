/**
 * PM2 example: monorepo root as cwd, Python entry at projects/bitcoin-trading.
 * Copy to VPS, adjust paths / interpreter, then: pm2 start pm2.ecosystem.example.cjs
 *
 * SSOT: docs/final/LOCAL_VS_VPS_ONE_RULE_WORKFLOW.md (VPS 배치)
 */
module.exports = {
  apps: [
    {
      name: "mkm-btc-live",
      cwd: "/opt/mkm-lab-workspace-v2",
      script: "projects/bitcoin-trading/start_live_trading.py",
      interpreter: "python3",
      instances: 1,
      autorestart: true,
      max_restarts: 20,
      min_uptime: "10s",
      // env: { PYTHONUNBUFFERED: "1" },
    },
  ],
};
