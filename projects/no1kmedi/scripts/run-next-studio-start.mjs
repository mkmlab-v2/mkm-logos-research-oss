#!/usr/bin/env node
import { spawnSync } from "node:child_process";

const port = process.env.LOGOS_STUDIO_PORT || "3203";
process.env.MKM_NEXT_DIST_DIR = ".next-studio";
const proc = spawnSync("npx", ["next", "start", "-p", port], {
  stdio: "inherit",
  shell: true,
  env: process.env,
});
process.exit(proc.status ?? 1);
