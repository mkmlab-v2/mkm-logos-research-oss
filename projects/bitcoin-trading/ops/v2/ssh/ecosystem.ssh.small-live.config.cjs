const path = require("path");

const repoRoot = path.resolve(__dirname, "../../../../../");
const projectRoot = path.join(repoRoot, "projects/bitcoin-trading");
const appScript = path.join(projectRoot, "start_live_trading.py");

module.exports = {
  apps: [
    {
      name: "bitcoin-live-small-24h",
      cwd: projectRoot,
      script: appScript,
      interpreter: "python3",
      watch: false,
      autorestart: true,
      restart_delay: 5000,
      max_memory_restart: "1G",
      env: {
        PYTHONUNBUFFERED: "1",
      },
    },
  ],
};
