/** PM2 — Hostinger VPS only (SSOT: NO1KMEDI_MKMLIFE_REPO_PATH_SSOT). Not hPanel shared hosting. */
module.exports = {
  apps: [
    {
      name: "no1kmedi-payapp-api",
      cwd: __dirname,
      script: "server.js",
      interpreter: "node",
      instances: 1,
      autorestart: true,
      max_restarts: 10,
      env: {
        NODE_ENV: "production",
        PORT: "3847",
      },
    },
  ],
};
