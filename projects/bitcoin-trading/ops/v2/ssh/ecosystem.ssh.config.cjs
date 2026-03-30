module.exports = {
  apps: [
    {
      name: "bitcoin-v2-shadow-15min",
      cwd: "/opt/bitcoin-trading",
      script: "ops/v2/ssh/loop_runner.py",
      interpreter: "/opt/bitcoin-trading/.venv/bin/python",
      watch: false,
      autorestart: true,
      max_memory_restart: "512M",
      restart_delay: 5000,
      env: {
        PYTHONUNBUFFERED: "1",
      },
      args: "--name shadow --interval-sec 900 --command \"/opt/bitcoin-trading/.venv/bin/python ops/v2/tasks/run_shadow_cycle.py\"",
    },
    {
      name: "bitcoin-v2-execute-guarded-15min",
      cwd: "/opt/bitcoin-trading",
      script: "ops/v2/ssh/loop_runner.py",
      interpreter: "/opt/bitcoin-trading/.venv/bin/python",
      watch: false,
      autorestart: true,
      max_memory_restart: "512M",
      restart_delay: 5000,
      env: {
        PYTHONUNBUFFERED: "1",
      },
      // Delay execute loop by 2 minutes to allow shadow cycle pre-state stabilization.
      args: "--name execute_guarded --interval-sec 900 --initial-delay-sec 120 --command \"/opt/bitcoin-trading/.venv/bin/python ops/v2/tasks/run_execute_cycle_guarded.py\"",
    },
    {
      name: "bitcoin-v2-opsdigest-30min",
      cwd: "/opt/bitcoin-trading",
      script: "ops/v2/ssh/loop_runner.py",
      interpreter: "/opt/bitcoin-trading/.venv/bin/python",
      watch: false,
      autorestart: true,
      max_memory_restart: "512M",
      restart_delay: 5000,
      env: {
        PYTHONUNBUFFERED: "1",
      },
      args: "--name ops_digest --interval-sec 1800 --initial-delay-sec 180 --command \"/opt/bitcoin-trading/.venv/bin/python ops/v2/reports/run_ops_digest.py --with-health\"",
    },
    {
      name: "bitcoin-v2-bible-insight-hourly",
      cwd: "/opt/bitcoin-trading",
      script: "ops/v2/ssh/loop_runner.py",
      interpreter: "/opt/bitcoin-trading/.venv/bin/python",
      watch: false,
      autorestart: true,
      max_memory_restart: "1G",
      restart_delay: 10000,
      env: {
        PYTHONUNBUFFERED: "1",
        // Override this in VPS env if you prefer another scripture insight generator.
        BIBLE_INSIGHT_COMMAND: "/opt/bitcoin-trading/.venv/bin/python /opt/workspace/scripts/final_prophecy_apocalypse_2026.py",
      },
      args: "--name bible_insight --interval-sec 3600 --initial-delay-sec 240 --command \"$BIBLE_INSIGHT_COMMAND\"",
    },
    {
      name: "bitcoin-v2-logos-core-hourly",
      cwd: "/opt/bitcoin-trading",
      script: "ops/v2/ssh/loop_runner.py",
      interpreter: "/opt/bitcoin-trading/.venv/bin/python",
      watch: false,
      autorestart: true,
      max_memory_restart: "512M",
      restart_delay: 10000,
      env: {
        PYTHONUNBUFFERED: "1",
      },
      // Domain-neutral core insight pipeline (finance is only one adapter).
      args: "--name logos_core --interval-sec 3600 --initial-delay-sec 300 --command \"/opt/bitcoin-trading/.venv/bin/python ops/v2/reports/run_logos_core_pipeline.py\"",
    },
  ],
};
