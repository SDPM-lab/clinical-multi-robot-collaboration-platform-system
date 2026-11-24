import {createRequire} from "node:module";
import {mkdir, writeFile} from "node:fs/promises";
import {resolve} from "node:path";
import {capturedAt, robotSnapshot, taskRecords} from "./dashboard-v2-demo.mjs";

const require = createRequire(import.meta.url);
const dependencyRoot = process.env.CAPTURE_DEPENDENCIES;
const {chromium} = require(dependencyRoot ? resolve(dependencyRoot, "node_modules/playwright") : "playwright");
const origin = "http://127.0.0.1:4179";
const output = new URL("../public/dashboard-v2/", import.meta.url);
await mkdir(output, {recursive: true});
const browser = await chromium.launch({
  executablePath: process.env.CAPTURE_CHROMIUM,
  args: ["--no-sandbox", "--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"],
});

try {
  const page = await browser.newPage({
    viewport: {width: 1600, height: 900}, deviceScaleFactor: 1,
    timezoneId: "Asia/Taipei", locale: "en-US", reducedMotion: "reduce",
  });
  await page.addInitScript(() => {
    localStorage.setItem("hospital-rmf-locale", "en");
    const raf = window.requestAnimationFrame.bind(window);
    window.requestAnimationFrame = callback => raf(time => {
      if (!window.freezeDashboardCapture) callback(time);
    });
  });
  let poll = 0;
  await page.clock.setFixedTime(capturedAt);
  await page.route("**/*", async route => {
    const url = new URL(route.request().url());
    const method = route.request().method();
    if (method === "GET" && url.pathname === "/api/auth/me") {
      return route.fulfill({json: {id: "film-preview", name: "MediSync Demo", email: "demo@example.invalid"}});
    }
    if (method === "GET" && url.pathname === "/api/robots") return route.fulfill({json: robotSnapshot(poll++)});
    if (method === "GET" && url.pathname === "/api/v1/task") return route.fulfill({json: taskRecords});
    if (url.origin !== origin || url.pathname.startsWith("/api/") || method !== "GET") return route.abort();
    return route.continue();
  });
  await page.routeWebSocket("**/*", socket => socket.close());
  await page.goto(origin, {waitUntil: "domcontentloaded"});
  await page.addStyleTag({content: `
    vite-plugin-vue-devtools, #vue-devtools__anchor, #vue-devtools__container,
    .clinic-overview-scene .shared-loading-leave-active {display:none!important}
    .right-information-stack *, .overview-bottom-main * {animation:none!important;transition:none!important}
    .schedule-list li {opacity:1!important}
  `});
  await page.waitForFunction(() => {
    const loading = document.querySelector(".clinic-overview-scene .scene-message");
    return document.querySelector(".clinic-building-stage canvas")
      && (!loading || loading.classList.contains("shared-loading-leave-active"))
      && document.querySelectorAll(".schedule-list li").length === 24
      && document.querySelector(".progress-content li");
  }, undefined, {polling: 300, timeout: 120000});
  await page.evaluate(() => document.fonts.ready);
  console.log("English UI, WebGL model, 24 schedule rows and task progress ready");
  const layout = await page.evaluate(() => {
    const rect = selector => {
      const {x, y, width, height} = document.querySelector(selector).getBoundingClientRect();
      return {x, y, width, height};
    };
    return {
      complete: rect(".completion-panel"), schedule: rect(".right-information-stack"),
      battery: rect(".overview-bottom-main"), fleet: rect(".overview-connectivity"),
      dispatch: rect(".overview-nav__link:nth-child(2)"),
    };
  });
  await page.evaluate(() => { window.freezeDashboardCapture = true; });
  const cdp = await page.context().newCDPSession(page);
  const {data} = await cdp.send("Page.captureScreenshot", {format: "png", fromSurface: true});
  await writeFile(new URL("overview.png", output), Buffer.from(data, "base64"));
  await writeFile(new URL("../src/dashboard-v2-layout.json", import.meta.url), JSON.stringify(layout, null, 2) + "\n");
  console.log("Dashboard V2 assets captured");
} finally {
  await browser.close();
}
