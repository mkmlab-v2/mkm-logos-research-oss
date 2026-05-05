import fs from "node:fs";
import path from "node:path";
import { chromium, devices } from "playwright";

const workspaceRoot = "c:/workspace";
const outputDir = path.join(workspaceRoot, "docs/final/artifacts/captures");
const desktopPath = path.join(outputDir, "jemaai_cloud_desktop_20260506_0015.png");
const mobilePath = path.join(outputDir, "jemaai_cloud_mobile_20260506_0015.png");
const targetUrl = "https://jemaai.cloud";

fs.mkdirSync(outputDir, { recursive: true });

const browser = await chromium.launch({ headless: true });

try {
  const desktopContext = await browser.newContext({
    viewport: { width: 1440, height: 900 },
  });
  const desktopPage = await desktopContext.newPage();
  await desktopPage.goto(targetUrl, { waitUntil: "domcontentloaded", timeout: 60000 });
  await desktopPage.waitForTimeout(4000);
  await desktopPage.screenshot({ path: desktopPath, fullPage: true });
  await desktopContext.close();

  const mobileContext = await browser.newContext({
    ...devices["iPhone 13"],
  });
  const mobilePage = await mobileContext.newPage();
  await mobilePage.goto(targetUrl, { waitUntil: "domcontentloaded", timeout: 60000 });
  await mobilePage.waitForTimeout(4000);
  await mobilePage.screenshot({ path: mobilePath, fullPage: true });
  await mobileContext.close();

  console.log(JSON.stringify({ ok: true, desktopPath, mobilePath }));
} finally {
  await browser.close();
}
