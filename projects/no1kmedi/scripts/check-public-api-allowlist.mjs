#!/usr/bin/env node

import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { glob } from "glob";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, "..");
const publicApiRoot = path.join(projectRoot, "src", "app", "api", "public");

const routeFiles = await glob("**/route.ts", { cwd: publicApiRoot, nodir: true });

if (routeFiles.length === 0) {
  console.log("[check-public-api-allowlist] no public route.ts found, skipping.");
  process.exit(0);
}

const violations = [];

for (const rel of routeFiles) {
  const abs = path.join(publicApiRoot, rel);
  const source = await readFile(abs, "utf8");
  const routeLabel = path.join("src", "app", "api", "public", rel);

  const spreadMatches = source.match(/\.\.\./g);
  if (spreadMatches && spreadMatches.length > 0) {
    violations.push(`${routeLabel}: spread operator (...) is forbidden in public API routes.`);
  }

  const hasNextResponseJson = /NextResponse\.json\(/.test(source);
  if (!hasNextResponseJson) {
    violations.push(`${routeLabel}: must return NextResponse.json(...) response contract.`);
  }

  const hasAllowlistSerializer = /function\s+toPublic[A-Za-z0-9_]*\s*\(/.test(source);
  if (!hasAllowlistSerializer) {
    violations.push(`${routeLabel}: missing toPublic* serializer function (allowlist contract).`);
  }
}

if (violations.length > 0) {
  console.error("[check-public-api-allowlist] FAILED");
  for (const line of violations) console.error(`- ${line}`);
  process.exit(1);
}

console.log(`[check-public-api-allowlist] passed (${routeFiles.length} route file(s)).`);
