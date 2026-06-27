#!/usr/bin/env node
import { spawnSync } from "node:child_process";

process.env.MKM_NEXT_DIST_DIR = ".next-studio";
const proc = spawnSync("npx", ["next", "build"], {
  stdio: "inherit",
  shell: true,
  env: process.env,
});
process.exit(proc.status ?? 1);
