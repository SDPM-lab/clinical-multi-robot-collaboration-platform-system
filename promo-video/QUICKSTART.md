# MediSync 影片原型

V7 使用 `DashboardRevealV4`，試看片為 `previews/DashboardRevealV4-540p.mp4`。
原生 Overview 與新版最後定格的並排比較為 `previews/DashboardRevealV4-Comparison.png`。
配音、相機及示範資料規格見 `DASHBOARD-REVEAL-V4.md`。

V6 試看片在 `previews/DashboardRevealV3-540p.mp4`。在 Studio 選
`DashboardRevealV3` 可預覽六層 Dashboard、臺灣華語配音和繁中字幕。
配音替換方式與資料來源見 `DASHBOARD-REVEAL-V3.md`。

V5 試看片在 `previews/DashboardRevealV2-540p.mp4`。在 Studio 選
`DashboardRevealV2` 可預覽新版。新版分鏡、配方與採集說明見
`DASHBOARD-REVEAL-V2.md`。

從 `promo-video` 執行 `npm run dev`，在 Remotion Studio 選取
`DashboardRevealPrototype`。原型為 1920 × 1080、30 fps、10 秒。

診所 WebGL 與 Dashboard 擷取自本地正式 Overview 元件，排程與車隊透過
瀏覽器攔截讀取隔離的模擬資料。成片內的運鏡使用這些擷取畫面做分層合成。
音訊是本原型的合成音效，落在揭幕、面板分離、掃光與合體四個動作附近。

使用的 Shotcraft 參考為 `space-camera-moves / ExplodedView` 的透視分層與合體、
`depth-layer-moves / MultiplaneReal` 的差速與視差，以及
`spotlight-sweep-moves / SlideSpotlightPan` 的局部掃光。

如需重擷取，先從 `frontend` 啟動
`npm run dev -- --host 127.0.0.1 --port 4179 --strictPort`。
安裝 Playwright 與 Chromium 後，從 `promo-video` 執行
`node scripts/capture-dashboard.mjs`。若 Playwright 裝在其他目錄，可設定
`CAPTURE_DEPENDENCIES` 指向其安裝根目錄。也可以用 `CAPTURE_CHROMIUM`
指定 Chromium 執行檔。
