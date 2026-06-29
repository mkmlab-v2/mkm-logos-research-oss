/**
 * PM2: AI Smartfarm API stub (port 8020) — pilot Phase 0/1
 *
 * Usage on VPS (after git pull):
 *   pm2 start /opt/mkm-destiny-ai-41e38ec6/scripts/deploy/linux/pm2_smartfarm_api.config.cjs
 *   pm2 save
 */
module.exports = {
  apps: [
    {
      name: "smartfarm-api",
      cwd: "/opt/mkm-destiny-ai-41e38ec6",
      script: "scripts/deploy/linux/run_smartfarm_api_v1.sh",
      interpreter: "bash",
      env: {
        PYTHONUNBUFFERED: "1",
        SMARTFARM_PILOT_FARM_ID: "geumsan_farm_01",
        SMARTFARM_PILOT_ZONE_ID: "zone_01",
        SMARTFARM_PILOT_TIMEZONE: "Asia/Seoul",
        SMARTFARM_QUBICS_RAW_JSONL:
          "/opt/mkm-destiny-ai-41e38ec6/reports/smartfarm_qubics_ingest.jsonl",
        SMARTFARM_EVENT_JSONL_PATH:
          "/opt/mkm-destiny-ai-41e38ec6/reports/smartfarm_api_events.jsonl",
        SMARTFARM_API_CORS_ALLOW_ORIGINS: "https://farm.jema-ai.com,https://farm.mkmlife.com",
      },
    },
  ],
};
