/**
 * Destiny monorepo VPS health monitor (watches bitcoin-live-small-24h only).
 * SSOT: docs/final/LOCAL_VS_VPS_ONE_RULE_WORKFLOW.md
 *
 *   cd /opt/mkm-destiny-ai-41e38ec6
 *   pm2 start projects/bitcoin-trading/ops/pm2.ecosystem.destiny-health.cjs
 *   pm2 save
 */
const destinyRoot =
  process.env.MKM_DESTINY_ROOT || "/opt/mkm-destiny-ai-41e38ec6";
const liveApp = process.env.PM2_LIVE_APP_NAME || "bitcoin-live-small-24h";

module.exports = {
  apps: [
    {
      name: "bitcoin-destiny-health-monitor",
      cwd: destinyRoot,
      script: "projects/bitcoin-trading/src/monitoring/vps_health_monitor.py",
      interpreter: "python3",
      instances: 1,
      autorestart: true,
      max_restarts: 10,
      min_uptime: "30s",
      max_memory_restart: "256M",
      env: {
        PYTHONUNBUFFERED: "1",
        PM2_PROCESS_NAME: liveApp,
        VPS_HEALTH_CHECK_INTERVAL: "60",
      },
    },
  ],
};
