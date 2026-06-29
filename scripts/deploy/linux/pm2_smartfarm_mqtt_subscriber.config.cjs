/**
 * PM2: QuBICS MQTT uplink subscriber (qbsv4 stat/evnt -> JSONL + HTTP ingest)
 *
 * Requires Mosquitto (or vendor broker) reachable from VPS + gateway G300 pointed at broker.
 *
 *   pm2 start scripts/deploy/linux/pm2_smartfarm_mqtt_subscriber.config.cjs
 *   pm2 save
 */
module.exports = {
  apps: [
    {
      name: "smartfarm-mqtt-subscriber",
      cwd: "/opt/mkm-destiny-ai-41e38ec6",
      script: "scripts/smartfarm_qubics_mqtt_subscriber_v1.py",
      interpreter: "/opt/mkm-destiny-ai-41e38ec6/.venv-smartfarm/bin/python",
      env: {
        PYTHONUNBUFFERED: "1",
        SMARTFARM_PILOT_FARM_ID: "geumsan_farm_01",
        SMARTFARM_PILOT_TIMEZONE: "Asia/Seoul",
        SMARTFARM_API_BASE_URL: "http://127.0.0.1:8020",
        SMARTFARM_QUBICS_DEVICE_MANIFEST:
          "/opt/mkm-destiny-ai-41e38ec6/docs/final/artifacts/smartfarm_qubics_device_manifest_v1.json",
        SMARTFARM_QUBICS_MQTT_JSONL:
          "/opt/mkm-destiny-ai-41e38ec6/reports/smartfarm_qubics_mqtt_uplink.jsonl",
        SMARTFARM_MQTT_BROKER_HOST: "127.0.0.1",
        SMARTFARM_MQTT_BROKER_PORT: "1883",
      },
    },
  ],
};
