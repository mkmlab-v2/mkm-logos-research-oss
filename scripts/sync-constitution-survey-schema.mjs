#!/usr/bin/env node

import { access } from "node:fs/promises";
import { constants as fsConstants } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const schemaPath = path.resolve(
  __dirname,
  "..",
  "projects",
  "no1kmedi",
  "src",
  "lib",
  "constitution-survey-schema.ts",
);

try {
  await access(schemaPath, fsConstants.F_OK);
  console.log(`[sync-constitution-survey-schema] schema found: ${schemaPath}`);
  console.log("[sync-constitution-survey-schema] no sync changes required.");
} catch (error) {
  console.error("[sync-constitution-survey-schema] schema file is missing.");
  console.error(`expected path: ${schemaPath}`);
  if (error instanceof Error && error.message) {
    console.error(error.message);
  }
  process.exitCode = 1;
}
