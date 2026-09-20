# Overview GLB 與局部視覺修正驗證

## GLB 結構與樓層 mapping

- 驗證模型：`public/models/clinic_overview.glb`，檔案大小 1,723,192 bytes。
- 最新匯入模型是單一 `Scene` 根節點；實際分類 525 個 mesh：Floor 1 為 91、Floor 2 為 72、Floor 3 為 127、共用／環境為 235，其中 8 個是跨樓層建築外殼。
- 實際節點族群包含 `Floor_1_Slab`、`F1_Left_*`、`F1_Right_*`、`RightGlass_F1_*`、`Floor_2_Slab`、`F2_Main_*`、`RightGlass_F2_*`、`Floor_3_Slab`、`F3_Main_*`、`RightGlass_F3_*`、`Third_Floor_Dark_Soffit`、`Upper_Balcony_Floor`、`Roof_*`、`Web_Roof_Downlight_*`。
- 集中 mapping 位於 `src/three/clinicFloorMapping.js`。名稱會先正規化，再依明確樓層命名分類；環境物件與跨樓層外殼各自辨識；只有未標記的建築節點才使用樓板高度 bounds fallback。
- 樓層模式保留環境，顯示所選樓層與其下樓層、淡化較低樓層並隱藏較高樓層；全棟模式還原每個 mesh 的原始 visible、單材質或多材質透明度、depthWrite 與 renderOrder。

## Loading 與相機

- `ClinicOverviewScene.vue` 和即時地圖的 `HospitalScene.vue` 直接引用同一個 `SharedLoading.vue`，共用環形動畫、尺寸、速度與文字樣式。
- Overview 以 `GLTFLoader` 的 progress event 計算 `loaded / total`；完成前最多顯示 99%，onLoad 後才切換為 100%。沒有使用 `setTimeout` 模擬進度。
- 本機模型回應提供 `Content-Length: 1723192`，`modelLoadPercentage` 的 0%、中段、99% 上限與缺少 total 情況已有單元測試。
- 套用的全棟模型 preset：position `(-2.6711178700891924, 3.9159005573132415, -0.0891364507224327)`、scale `0.8951884436412747`、rotationY `0.40120019531249995`。
- 相機 position `(13.8976, 10.9799, 26.144)`，target `(-1.265, 6.1971, 2.9808)`。全棟與樓層切換不會覆蓋這組已確認數值。

## 瀏覽器驗證

| 狀態 | 可見樓層 | Bottom panel | 全棟材質還原 |
| --- | --- | --- | --- |
| 全棟 | F1 91 / F2 72 / F3 127 | 全棟電量趨勢 | altered materials 0 |
| Floor 1 | F1 91 | 單樓層機器人狀態 | 通過 |
| Floor 2 | F1 91 / F2 72 | 單樓層機器人狀態 | 通過 |
| Floor 3 | F1 91 / F2 72 / F3 127 | 單樓層機器人狀態 | 通過 |
| 返回全棟 | F1 91 / F2 72 / F3 127 | 全棟電量趨勢 | altered materials 0 |

- 依序檢查全棟 → Floor 1 → Floor 2 → Floor 3 → 全棟；返回後相機 position、target 與 preset 完全一致。
- 1440×900 與 1920×1080 的 `documentElement.scrollWidth` 均等於 viewport width，沒有橫向 overflow。
- Navbar 保持透明並沿用頁面背景；Overview 背景使用珍珠白底與低透明度、固定位置的暖黃／冷色柔光，不使用橘色日落大片漸層。
- 排程歷史五個統計背景皆來自 `historyStatisticThemes`，五組值互不相同；切換資料時保留 count-up、淡入與輕微背景亮度 transition。

## 自動驗證

- TypeScript：`./node_modules/.bin/tsc --noEmit` 通過。專案未安裝 `vue-tsc`，直接執行 `npx vue-tsc` 會嘗試連線 npm registry，因此未把下載失敗當作型別結果。
- Unit tests：35 個 test files、115 個 tests 全數通過。
- Production build：Vite build 通過；保留既有單一 chunk 超過 500 kB 的提示。
- Lint：`package.json` 沒有 `lint` script，因此沒有可執行的既有 lint 工作。
