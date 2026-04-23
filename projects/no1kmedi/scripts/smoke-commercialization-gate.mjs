#!/usr/bin/env node
import { spawn } from "node:child_process";
import net from "node:net";

const requireLive = process.argv.includes("--require-live");

function getFreePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.listen(0, "127.0.0.1", () => {
      const addr = server.address();
      if (!addr || typeof addr === "string") {
        server.close();
        reject(new Error("failed to allocate free port"));
        return;
      }
      const port = addr.port;
      server.close(() => resolve(port));
    });
    server.on("error", reject);
  });
}

function waitForServerReady(baseUrl, timeoutMs = 60_000) {
  const startedAt = Date.now();
  return new Promise((resolve, reject) => {
    const poll = async () => {
      try {
        const res = await fetch(`${baseUrl}/`);
        if (res.status < 500) {
          resolve();
          return;
        }
      } catch {}
      if (Date.now() - startedAt > timeoutMs) {
        reject(new Error("dev server boot timeout"));
        return;
      }
      setTimeout(poll, 1000);
    };
    poll();
  });
}

function runNodeScript(scriptPath, env) {
  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, [scriptPath], { stdio: "inherit", env });
    child.on("exit", (code) => (code === 0 ? resolve() : reject(new Error(`${scriptPath} exited with code ${code}`))));
    child.on("error", reject);
  });
}

/** Node 22+ strip-types smoke (no Next dev server). */
function runStripTypesModule(scriptPath, env) {
  return new Promise((resolve, reject) => {
    const child = spawn(
      process.execPath,
      ["--disable-warning=MODULE_TYPELESS_PACKAGE_JSON", "--experimental-strip-types", scriptPath],
      { stdio: "inherit", env },
    );
    child.on("exit", (code) => (code === 0 ? resolve() : reject(new Error(`${scriptPath} exited with code ${code}`))));
    child.on("error", reject);
  });
}

async function main() {
  await runStripTypesModule("./scripts/smoke-guardian-llm-priority.mts", process.env);

  const port = await getFreePort();
  const baseUrl = `http://127.0.0.1:${port}`;
  const env = { ...process.env, NO1KMEDI_BASE_URL: baseUrl };

  const dev = spawn("npx", ["next", "dev", "-H", "127.0.0.1", "-p", String(port)], {
    stdio: "inherit",
    shell: process.platform === "win32",
    env,
  });

  try {
    await waitForServerReady(baseUrl);
    await runNodeScript("./scripts/smoke-advanced-consult.mjs", {
      ...env,
      ...(requireLive ? { NO1KMEDI_REQUIRE_LIVE: "1" } : {}),
    });
    await runNodeScript("./scripts/smoke-partner-clinic-chat.mjs", env);
    await runNodeScript("./scripts/smoke-guardian-ai-chat.mjs", env);
    await runNodeScript("./scripts/smoke-guardian-ai-post.mjs", env);
    await runNodeScript("./scripts/smoke-member-access-flow.mjs", env);
    console.log(`smoke-commercialization-gate passed (${requireLive ? "live" : "standard"})`);
  } finally {
    dev.kill();
  }
}

main().catch((error) => {
  console.error("smoke-commercialization-gate failed:", error.message);
  process.exit(1);
});
