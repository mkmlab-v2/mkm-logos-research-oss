#!/usr/bin/env node
import fs from "fs/promises";
import path from "path";

const root = process.cwd();
const forbidden = /(성경|사상|명리|사주|팔자|sasang|myeongri|scripture|logos)/i;
const exts = new Set([".ts", ".tsx", ".js", ".jsx", ".mjs", ".json", ".md", ".html", ".css"]);
const publicScopes = ["marketing-site", "src/app", "src/app/api/public"];
const skipDirs = new Set(["node_modules", ".next", ".git", "memory", "data"]);

async function walk(dir, out) {
  const entries = await fs.readdir(dir, { withFileTypes: true });
  for (const entry of entries) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (skipDirs.has(entry.name)) continue;
      await walk(full, out);
      continue;
    }
    if (!exts.has(path.extname(entry.name).toLowerCase())) continue;
    out.push(full);
  }
}

async function main() {
  const files = [];
  for (const scope of publicScopes) {
    const abs = path.join(root, scope);
    try {
      const stat = await fs.stat(abs);
      if (stat.isDirectory()) await walk(abs, files);
    } catch {
      // Scope may not exist in all deployments.
    }
  }

  const hits = [];
  for (const file of files) {
    const rel = path.relative(root, file);
    const text = await fs.readFile(file, "utf8");
    const lines = text.split(/\r?\n/);
    for (let i = 0; i < lines.length; i += 1) {
      if (forbidden.test(lines[i])) {
        hits.push(`${rel}:${i + 1}:${lines[i].trim()}`);
      }
    }
  }

  if (hits.length > 0) {
    console.error("[OPSEC] Forbidden terms found in public scopes:");
    for (const line of hits) console.error(` - ${line}`);
    process.exit(1);
  }

  console.log("[OPSEC] OK - no forbidden terms in public scopes.");
}

main().catch((error) => {
  console.error("[OPSEC] check failed:", error?.message || String(error));
  process.exit(1);
});
