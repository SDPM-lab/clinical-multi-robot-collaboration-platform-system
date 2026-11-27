import {createRequire} from "node:module";
import {mkdir, writeFile} from "node:fs/promises";
import {resolve} from "node:path";

const require = createRequire(import.meta.url);
const dependencyRoot = process.env.CAPTURE_DEPENDENCIES;
const {chromium} = require(dependencyRoot ? resolve(dependencyRoot, "node_modules/playwright") : "playwright");
const origin = "http://127.0.0.1:4179";
const output = new URL("../public/dashboard-reveal/", import.meta.url);
await mkdir(output, {recursive: true});
const browser = await chromium.launch({
  executablePath: process.env.CAPTURE_CHROMIUM,
  args: ["--no-sandbox", "--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"],
});

try {
  const page = await browser.newPage({viewport: {width: 1920, height: 1080}, deviceScaleFactor: 1, timezoneId: "Asia/Taipei"});
  await page.addInitScript(() => {
    const request = window.requestAnimationFrame.bind(window);
    window.requestAnimationFrame = callback =>
      request(time => { if (!window.__freezeCapture) callback(time); });
  });
  const capturedAt = new Date("2026-11-20T10:24:00+08:00");
  await page.clock.setFixedTime(capturedAt);
  const time = capturedAt.toISOString();
  const robots = [86, 61, 92, 79, 73, 50, 38].map((battery, index) => ({
    id: `robot-hospital_robot_${index + 1}`, levelName: "L1", hasTelemetry: true,
    status: index === 0 ? "執行任務中" : index === 6 ? "充電中" : "待命",
    battery, location: "reception_back", lastUpdate: time,
  }));
  const records = ["completed", "running", "pending"].map((status, index) => ({
    id: `film-overview-${index}`, taskCode: `T001${index}`,
    taskType: "medication_delivery", source: "reception_back", destination: "ward_a_1",
    scheduledAt: new Date(capturedAt.getTime() + (index - 1) * 3600000).toISOString(),
    assignedRobot: robots[index].id, status,
  }));
  await page.route("**/*", async route => {
    const url = new URL(route.request().url());
    if (url.pathname.endsWith("/api/auth/me")) {
      return route.fulfill({json: {id: "film-preview", name: "MediSync Demo", email: "demo@example.invalid"}});
    }
    if (route.request().method() === "GET" && url.pathname === "/api/robots") return route.fulfill({json: {robots}});
    if (route.request().method() === "GET" && url.pathname === "/api/v1/task") return route.fulfill({json: records});
    if (url.origin !== origin || url.pathname.startsWith("/api/")) return route.abort();
    return route.continue();
  });
  await page.routeWebSocket("**/*", socket => socket.close());
  await page.goto(origin, {waitUntil: "domcontentloaded"});
  console.log("Overview document loaded");
  await page.locator(".clinic-building-stage canvas").waitFor({timeout: 45000});
  await page.evaluate(() => document.fonts.ready);
  await page.addStyleTag({content: ".clinic-overview-scene .shared-loading-leave-active{display:none!important}"});
  await page.waitForFunction(() => {
    const message = document.querySelector(".clinic-overview-scene .scene-message");
    return !message || message.classList.contains("shared-loading-leave-active");
  }, undefined, {timeout: 90000, polling: 250});
  console.log("Clinic WebGL scene ready");
  await page.waitForFunction(() => document.querySelector(".dashboard-data-status")?.dataset.state === "fresh", undefined, {polling: 250, timeout: 90000});
  await page.addStyleTag({content: "vite-plugin-vue-devtools, #vue-devtools__anchor{display:none!important} .right-information-stack *{animation-delay:0s!important;animation-duration:.01ms!important}"});
  await page.evaluate(() => {
    const label = document.createElement("div");
    label.textContent = "模擬場景 · SIMULATION";
    label.style.cssText = "position:fixed;top:55px;left:20px;z-index:99999;font:600 13px system-ui;color:#713606;background:#fff0e0;border-radius:4px;padding:4px 8px";
    document.body.append(label);
  });
  await page.waitForTimeout(350);

  const groups = [
    ["completion", ".completion-panel", 20, -12, 85],
    ["schedule", ".right-information-stack", 25, 12, 95],
    ["status", ".bottom-status-panel", -16, 18, 120],
  ];
  const layout = await page.evaluate(groups => groups.map(([name, selector, dx, dy, depth]) => {
    const box = document.querySelector(selector)?.getBoundingClientRect();
    if (!box || box.bottom > 1080.5) throw new Error("Invalid panel bounds: " + selector);
    return {name, x: box.x, y: box.y, width: box.width, height: box.height, dx, dy, depth};
  }), groups);
  await page.evaluate(() => { window.__freezeCapture = true; });
  const cdp = await page.context().newCDPSession(page);
  const screenshot = async () => {
    const {data} = await cdp.send("Page.captureScreenshot", {
      format: "png", fromSurface: true, captureBeyondViewport: false,
    });
    return Buffer.from(data, "base64");
  };
  const overview = await screenshot();
  console.log("Overview frame captured");
  await page.addStyleTag({content: groups.map(([, selector]) => selector).join(",") + "{visibility:hidden!important}"});
  const base = await screenshot();
  await writeFile(new URL("overview.png", output), overview);
  await writeFile(new URL("base.png", output), base);
  await writeFile(new URL("../src/dashboard-layout.json", import.meta.url), JSON.stringify(layout, null, 2) + "\n");
} finally {
  await browser.close();
}
